import click
import socket
import json
import secrets
import docker
import subprocess
import psycopg
import time

from src.ComposeManager import ComposeManager
from src.EnvManager import EnvManager
from src.Services import OdooComposeService, ProxyComposeService, PostgresComposeService, KwkhtmltopdfComposeService
from src.errors import ServiceAlreadyExistsException, ServiceDoesNotExistException


PASSWORD_LENGTH = 32

DB_PORT = 5432
DB_USER = 'postgres'
DEFAULT_DB = 'postgres'

SERVICE_READY_WAIT_TIME = 300  # 300 seconds = 5 minutes

compose_manager = ComposeManager()
env_manager = EnvManager()


@click.group()
def cli():
    # Check if Docker is installed & running
    docker_version, compose_version = get_docker_versions()
    if docker_version is None or compose_version is None:
        click.echo("Docker and/or Docker Compose are not installed or running.", err=True)
        exit(2)
    pass


def get_local_ip():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


def check_domain_and_subdomain(domain):
    local_ip = get_local_ip()
    try:
        domain_ip = socket.gethostbyname(domain)
        test_subdomain_ip = socket.gethostbyname(f'test.{domain}')
        return domain_ip == local_ip and test_subdomain_ip == local_ip
    except socket.gaierror:
        # TODO: For Debugging = True Change it back!!!
        return True


def get_docker_client():
    return docker.from_env()


def get_docker_versions():
    try:
        client = get_docker_client()
        docker_version = client.version()['Version']
    except Exception as e:
        docker_version = None

    try:
        docker_compose_version = \
            subprocess.run(['docker-compose', '--version'], capture_output=True, text=True).stdout.strip().split()[
                3].replace('v', '')
    except Exception:
        docker_compose_version = None

    return docker_version, docker_compose_version


@cli.command()
@click.option('--json', 'return_json', is_flag=True, help='Output the data in JSON format', )
def inspect(return_json):
    initialized = compose_manager.initiated
    domain = env_manager.read_value('DOMAIN') if initialized else 'Not initialized'

    # Count the number of dev environments with the "pr_" prefix
    num_dev_envs = sum(1 for service_name in compose_manager.services.keys() if service_name.startswith("odoo_dev"))

    docker_version, docker_compose_version = get_docker_versions()
    docker_installed = docker_version is not None
    docker_compose_installed = docker_compose_version is not None
    domain_configured = check_domain_and_subdomain(domain) if initialized else None

    try:
        db_health = get_service_health('db') if initialized else None
    except docker.errors.NotFound:
        db_health = None

    try:
        proxy_health = get_service_health('proxy') if initialized else None
    except docker.errors.NotFound:
        proxy_health = None

    if return_json:
        # Output data in JSON format
        data = {
            "state": {
                "initialized": initialized,
                "domain": domain,
                "num_dev_envs": num_dev_envs,
                "docker_version": docker_version,
                "docker_compose_version": docker_compose_version,
                "db_health": db_health,
                "proxy_health": proxy_health
            },
            "checklist": {
                "domain_configured": domain_configured,
                "subdomain_configured": domain_configured,
                "docker_installed": docker_installed,
                "docker_compose_installed": docker_compose_installed
            }
        }
        click.echo(json.dumps(data, indent=4))
    else:
        # Output data in human-readable format
        click.echo("State:")
        click.echo(f"  Initialized: {'Yes' if initialized else 'No'}")
        click.echo(f"  Domain: {domain}")
        click.echo(f"  Number of dev environments: {num_dev_envs}")
        click.echo(f"  Docker version: {docker_version}")
        click.echo(f"  Docker Compose version: {docker_compose_version}")
        click.echo(f"  Database health: {db_health}")
        click.echo(f"  Proxy health: {proxy_health}")

        click.echo("\nChecklist:")
        if initialized:
            click.echo(f"  - Domain configured: {'✓' if domain_configured else '✗'}")
            click.echo(f"  - Subdomain configured: {'✓' if domain_configured else '✗'}")
        else:
            click.echo("  - Domain configured: N/A (not initialized)")
            click.echo("  - Subdomain configured: N/A (not initialized)")
        click.echo(f"  - Docker installed: {'✓' if docker_installed else '✗'}")
        click.echo(f"  - Docker Compose installed: {'✓' if docker_compose_installed else '✗'}")


def generate_password(length=PASSWORD_LENGTH) -> str:
    return secrets.token_urlsafe(length)


@cli.command()
@click.argument('domain')
def init(domain):
    # Check if .env file already exists
    if compose_manager.initiated:
        click.echo("Configuration has already been initialized.", err=True)
        exit(1)

    # Check if domain and subdomains point to the current server
    if not check_domain_and_subdomain(domain):
        click.echo(
            f"Domain and subdomains must point to this server's IP. Please ensure the domain and subdomains are correctly configured.",
            err=True)
        exit(1)

    master_db_password = generate_password()

    live_db_password = generate_password()
    pre_db_password = generate_password()

    # Save data to .env file
    env_manager.add_value('DOMAIN', domain)
    env_manager.add_value('MASTER_DB_PASSWORD', master_db_password)
    env_manager.add_value('LIVE_DB_PASSWORD', live_db_password)
    env_manager.add_value('PRE_DB_PASSWORD', pre_db_password)
    env_manager.save()

    click.echo('Setup initialized successfully.')

    # Run generate command
    ctx = click.get_current_context()
    ctx.invoke(generate)

    compose_manager.up(['db'])

    postgres_add_user('live', live_db_password)
    postgres_add_user('pre', pre_db_password)

    compose_manager.up()


def ensure_services_healthy(service_names):
    client = get_docker_client()

    start_time = time.time()

    first_check = True

    for service_name in service_names:
        # Continue looping until the service is healthy or the timeout is reached
        while True:
            # Check if the timeout has been reached
            elapsed_time = time.time() - start_time
            if elapsed_time > SERVICE_READY_WAIT_TIME:
                click.echo(f"Timeout reached while waiting for {service_name} to become healthy.", err=True)
                exit(4)

            # Get the service
            try:
                container = client.containers.get(service_name)
            except docker.errors.NotFound:
                click.echo(f"The {service_name} service is not running.", err=True)
                exit(5)

            # Get the health status
            health_status = get_service_health(service_name)

            if health_status == 'healthy':
                if not first_check:
                    click.echo(f"{service_name} is now healthy.")
                break
            elif health_status == 'unhealthy':
                click.echo(f"{service_name} is unhealthy. Please check your service.", err=True)
                exit(6)

            # Sleep for a while before checking the status again
            click.echo(f"Waiting for {service_name} to become healthy...")
            first_check = False
            time.sleep(5)


@cli.command()
@click.option('--dashboard', is_flag=True, help='Enable insecure API for the proxy service.')
def generate(dashboard):
    if not env_manager.initiated:
        click.echo("Please run the 'init' command before generating the configuration.", err=True)
        exit(1)
    domain = env_manager.read_value('DOMAIN')

    # Store domain in the proxy service for later reference
    proxy_service = ProxyComposeService(name='proxy', domain=domain, dashboard=dashboard)
    live_service = OdooComposeService(name='live', domain=domain, db_password='${LIVE_DB_PASSWORD}',
                                      admin_passwd=generate_password())  # Generate a random password each time because it will never be needed
    pre_service = OdooComposeService(name='pre', domain=f'pre.{domain}', db_password='${PRE_DB_PASSWORD}',
                                     admin_passwd=generate_password())
    db_service = PostgresComposeService(name='db')
    kwkhtmltopdf_service = KwkhtmltopdfComposeService(name='kwkhtmltopdf')

    # Update services
    compose_manager.set_service(proxy_service)
    compose_manager.set_service(live_service)
    compose_manager.set_service(pre_service)
    compose_manager.set_service(db_service)
    compose_manager.set_service(kwkhtmltopdf_service)

    # Write Docker Compose file
    compose_manager.save()

    click.echo(f"Docker Compose file 'docker-compose.yml' updated successfully.")


@cli.group()
def manage_dev_env():
    pass


def get_service_health(service_name):
    client = get_docker_client()
    # Get the service
    try:
        container = client.containers.get(service_name)
    except docker.errors.NotFound:
        click.echo(f"No service found with the name {service_name}.", err=True)
        raise

    # Get the health status
    return container.attrs.get('State', {}).get('Health', {}).get('Status')


@manage_dev_env.command()
@click.argument('pr_number')
def add(pr_number):
    if not compose_manager.initiated:
        click.echo("Please run the 'init' command before running this command.", err=True)
        exit(1)

    domain = env_manager.read_value('DOMAIN')
    service_name = f'odoo_dev_pr{pr_number}'

    dev_service = OdooComposeService(name=service_name, domain=f'pr{pr_number}.{domain}',
                                     db_password=f'{service_name}_DB_PASSWORD', admin_passwd=generate_password())

    try:
        compose_manager.add_service(dev_service)
    except ServiceAlreadyExistsException:
        click.echo(f"Development environment for PR{pr_number} already exists.", err=True)
        exit(1)

    db_password = generate_password()

    postgres_add_user(service_name, db_password)

    compose_manager.save()
    env_manager.add_value(f'{service_name}_DB_PASSWORD', db_password)
    env_manager.save()
    click.echo(f"Development environment for PR{pr_number} added successfully.")


@manage_dev_env.command()
@click.argument('pr_number')
def remove(pr_number):
    if not compose_manager.initiated:
        click.echo("Please run the 'init' command before running this command.", err=True)
        exit(1)

    service_name = f'odoo_dev_pr{pr_number}'

    try:
        compose_manager.remove_service(service_name)
    except ServiceDoesNotExistException:
        click.echo(f"Development environment for PR{pr_number} does not exist.", err=True)
        exit(1)

    compose_manager.save()
    postgres_remove_user(service_name)
    env_manager.remove_value(f'{service_name}_DB_PASSWORD')
    env_manager.save()
    click.echo(f"Development environment for PR{pr_number} removed successfully.")


def postgres_add_user(name: str, password: str) -> bool:
    try:
        with connect_postgres() as conn:
            conn.autocommit = True
            conn.execute(f"""CREATE ROLE {name} LOGIN CREATEDB PASSWORD \'{password}\'""")
        return True
    except Exception as e:
        click.echo(f"Failed to add user {name}: {e}", err=True)
        raise


def postgres_remove_user(name: str) -> bool:
    try:
        with connect_postgres() as conn:
            conn.autocommit = True
            conn.execute(f"""DROP ROLE IF EXISTS {name}""")
        return True
    except Exception as e:
        click.echo(f"Failed to remove user {name}: {e}", err=True)
        raise


def connect_postgres():
    ensure_services_healthy(['db'])

    db_password = env_manager.read_value('MASTER_DB_PASSWORD')
    return psycopg.connect(
        f"host=127.0.0.1 port={DB_PORT} dbname={DEFAULT_DB} user={DB_USER} password={db_password}")


@manage_dev_env.command()
def remove_all():
    if not compose_manager.initiated:
        click.echo("Please run the 'init' command before running this command.", err=True)
        exit(1)

    removed = False
    # List services to avoid "dictionary changed size during iteration" error
    for service_name in [key for key in compose_manager.services.keys() if key.startswith("odoo_dev")]:
        pr_number = service_name.split('pr')[-1]
        # Using click's context to call the remove function
        ctx = click.get_current_context()
        result = ctx.invoke(remove, pr_number=pr_number)
        removed = True
    if not removed:
        click.echo("No development environments found.", err=True)
        exit(4)

    click.echo("All development environments removed successfully.")


@cli.command()
@click.argument('new_domain')
def change_domain(new_domain):
    env_manager.update_value('DOMAIN', new_domain)
    env_manager.save()
    click.echo(f"Domain changed to {new_domain}.")

    ctx = click.get_current_context()
    ctx.invoke(generate)


if __name__ == '__main__':
    cli()
