import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import uuid

import click
import docker
import psycopg

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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def check_domain_and_subdomain(domain):
    local_ip = get_local_ip()
    domain_ip = socket.gethostbyname(domain)
    test_subdomain_ip = socket.gethostbyname(f'test.{domain}')
    return domain_ip == local_ip and test_subdomain_ip == local_ip


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
            subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True).stdout.strip().split()[
                3].replace('v', '')
    except Exception:
        docker_compose_version = None

    return docker_version, docker_compose_version


@cli.command()
@click.option('--json', 'return_json', is_flag=True, help='Output the data in JSON format', )
def inspect(return_json):
    initialized = compose_manager.initiated
    domain = env_manager.read_value('DOMAIN') if initialized else 'Not initialized'
    odoo_version = env_manager.read_value('VERSION') if initialized else 'Not initialized'

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
        data = {"state": {"initialized": initialized, "domain": domain, "odoo_version": odoo_version,
            "num_dev_envs": num_dev_envs, "docker_version": docker_version,
            "docker_compose_version": docker_compose_version, "db_health": db_health, "proxy_health": proxy_health},
            "checklist": {"domain_configured": domain_configured, "subdomain_configured": domain_configured,
                "docker_installed": docker_installed, "docker_compose_installed": docker_compose_installed}}
        click.echo(json.dumps(data, indent=4))
    else:
        # Output data in human-readable format
        click.echo("State:")
        click.echo(f"  Initialized: {'Yes' if initialized else 'No'}")
        click.echo(f"  Domain: {domain}")
        click.echo(f"  Odoo version: {odoo_version}")
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
@click.argument('version')
@click.option('--dev', '-d', is_flag=True, help='Enable development mode. No https and other dev related things')
def init(domain, version, dev):
    # Check if .env file already exists
    if compose_manager.initiated:
        click.echo("Configuration has already been initialized.", err=True)
        exit(1)

    # Check if domain and subdomains point to the current server
    if not dev and not check_domain_and_subdomain(domain):
        click.echo(
            f"Domain and subdomains must point to this server's IP. Please ensure the domain and subdomains are correctly configured.",
            err=True)
        exit(1)

    # TODO: Check if we have access to images

    master_db_password = generate_password()

    live_db_password = generate_password()
    pre_db_password = generate_password()

    # Save data to .env file
    env_manager.add_value('DEV', '1' if dev else '0')
    env_manager.add_value('DOMAIN', domain)
    env_manager.add_value('VERSION', version)
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
    version = env_manager.read_value('VERSION')
    is_dev = True if env_manager.read_value('DEV') == '1' else False

    # Store domain in the proxy service for later reference
    proxy_service = ProxyComposeService(name='proxy', domain=domain, dashboard=dashboard, https=not is_dev)
    live_service = OdooComposeService(name='live', domain=domain, db_password='${LIVE_DB_PASSWORD}',
                                      admin_passwd=generate_password(), odoo_version=version, basic_auth=False,
                                      https=not is_dev)  # Generate a random password each time because it will never be needed
    pre_service = OdooComposeService(name='pre', domain=f'pre.{domain}', db_password='${PRE_DB_PASSWORD}',
                                     admin_passwd=generate_password(), odoo_version=version, https=not is_dev)
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
    version = env_manager.read_value('VERSION')
    is_dev = True if env_manager.read_value('DEV') == '1' else False
    service_name = f'odoo_dev_pr{pr_number}'

    dev_service = OdooComposeService(name=service_name, domain=f'pr{pr_number}.{domain}',
                                     db_password=f'{service_name}_DB_PASSWORD', admin_passwd=generate_password(),
                                     odoo_version=version, https=not is_dev)

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


def connect_postgres(db: str = None):
    ensure_services_healthy(['db'])

    db = db or DEFAULT_DB

    db_password = env_manager.read_value('MASTER_DB_PASSWORD')
    return psycopg.connect(f"host=127.0.0.1 port={DB_PORT} dbname={db} user={DB_USER} password={db_password}")


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


def postgres_remove_db(name: str) -> bool:
    if name.lower() == 'live':
        click.echo("Cannot remove the live database.", err=True)
        exit(1)
    try:
        with connect_postgres() as conn:
            conn.autocommit = True
            conn.execute(f"""DROP DATABASE IF EXISTS {name}""")
        return True
    except Exception as e:
        click.echo(f"Failed to remove database {name}: {e}", err=True)
        raise


def dump_db(name: str, destination: str) -> str:
    path = f'{destination}/{name}_{uuid.uuid4()}.dump'

    result = subprocess.run(['docker', 'compose', 'exec', 'db', 'sh', '-c', f'pg_dump -U postgres -Fc {name} > {path}'],
                            capture_output=True, text=True)

    result.check_returncode()

    return path


def restore_db(db: str, user: str, file_source: str) -> bool:
    result = subprocess.run(['docker', 'compose', 'exec', 'db', 'sh', '-c',
                             f'pg_restore --clean --if-exists --no-acl --no-owner -d {db} -U {user} {file_source}'],
                            capture_output=True, text=True)

    result.check_returncode()

    return True


def postgres_add_db(name: str, user: str) -> bool:
    if name.lower() == 'live':
        click.echo("Cannot create the live database manually.", err=True)
        exit(1)

    try:
        with connect_postgres() as conn:
            conn.autocommit = True
            conn.execute(f"""CREATE DATABASE {name} OWNER {user}""")
        return True
    except Exception as e:
        click.echo(f"Failed to remove database {name}: {e}", err=True)
        raise


def remove_file_in_container(container_name: str, path: str, recursive: bool = False) -> bool:
    rm_command = 'rm'

    if recursive:
        rm_command += ' -r'

    result = subprocess.run(['docker', 'compose', 'exec', container_name, 'sh', '-c', f'{rm_command} {path}'],
                            capture_output=True, text=True)

    result.check_returncode()

    return True


def escape_db(name: str) -> bool:
    if name.lower() == 'live':
        click.echo("Cannot escape the live database manually.", err=True)
        exit(1)

    escape_statements = {'fetchmail_server': 'DELETE FROM fetchmail_server;',
        'ir_mail_server': 'DELETE FROM ir_mail_server;', 'ir_cron': 'UPDATE ir_cron SET active = FALSE;',
        'ir_config_parameter': f"UPDATE ir_config_parameter SET value = '{uuid.uuid4()}' WHERE key = 'database.uuid';"}

    def table_exists(conn, table_name):
        query = f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}');"
        cur = conn.execute(query)
        return cur.fetchone()[0]

    try:
        with connect_postgres(name) as conn:
            conn.autocommit = True
            for table, escape_statement in escape_statements.items():
                if not table_exists(conn, table):
                    click.echo(f"Table {table} does not exist. Skipping...", err=True)
                    continue
                conn.execute(escape_statement)
        return True
    except Exception as e:
        click.echo(f"Failed to escape database {name}: {e}", err=True)
        raise


@cli.command()
@click.argument('enviroment')
def refresh_enviroment(enviroment):
    if not compose_manager.initiated:
        click.echo("Please run the 'init' command before running this command.", err=True)
        exit(1)

    if enviroment == 'live':
        click.echo("Cannot refresh the live environment.", err=True)
        exit(1)

    if get_service_health('db') != 'healthy':
        click.echo("The database service is not healthy.", err=True)
        exit(1)

    if enviroment not in ['live', 'pre']:
        # Check if the environment exists
        if enviroment not in compose_manager.services.keys() or not enviroment.startswith('odoo'):
            click.echo(f"The environment {enviroment} does not exist or isn't an odoo env.", err=True)
            exit(1)

    click.echo(f"Refreshing {enviroment} environment")

    click.echo("* Stopping environment")
    compose_manager.stop([enviroment])

    click.echo("* Removing old database")
    postgres_remove_db(enviroment)

    click.echo("* Copy new database")
    path = dump_db('live', '/tmp')

    click.echo('* Restore dump')
    postgres_add_db(enviroment, enviroment)
    restore_db(enviroment, enviroment, path)

    click.echo('* Remove dump')
    remove_file_in_container('db', path)

    click.echo('* Copy Filestore')
    enviroment_folder_path = f'volumes/{enviroment}/filestore/pre'
    live_folder_path = 'volumes/live/filestore/live'

    if os.path.exists(enviroment_folder_path):
        shutil.rmtree(enviroment_folder_path)

    shutil.copytree(live_folder_path, enviroment_folder_path)

    click.echo('* Escape new DB')
    escape_db(enviroment)

    click.echo("* Starting environment")
    compose_manager.up([enviroment])


if __name__ == '__main__':
    cli()
