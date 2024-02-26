import click

from src.DatabaseManager import DatabaseManager
from src.Services import OdooComposeService
from src.constants import DB_USER, DEFAULT_DB
from src.errors import ServiceAlreadyExistsException, ServiceDoesNotExistException
from src.helper import generate_password, copy_files_from_container


@click.group()
def manage_dev_env():
    pass


@manage_dev_env.command()
@click.argument('pr_number')
@click.pass_context
def add(ctx, pr_number):
    compose_manager = ctx.obj['compose_manager']
    env_manager = ctx.obj['env_manager']
    if not compose_manager.initiated:
        click.echo("Please run the 'init' command before running this command.", err=True)
        exit(1)

    domain = env_manager.read_value('DOMAIN')
    version = env_manager.read_value('VERSION')
    is_dev = env_manager.read_value('DEV', '0') == '1'
    module_mode = env_manager.read_value('MODULE_MODE') if env_manager.read_value('MODULE_MODE') else 'included'
    service_name = f'odoo_dev_pr{pr_number}'

    dev_service = OdooComposeService(name=service_name, domain=f'pr{pr_number}.{domain}',
                                     db_password=f'{service_name}_DB_PASSWORD', admin_passwd=generate_password(),
                                     odoo_version=version, https=not is_dev, module_mode=module_mode)

    try:
        compose_manager.add_service(dev_service)
    except ServiceAlreadyExistsException:
        click.echo(f"Development environment for PR{pr_number} already exists.", err=True)
        exit(1)

    db_password = generate_password()

    DatabaseManager(DEFAULT_DB, DB_USER, env_manager.read_value('MASTER_DB_PASSWORD')).add_user(service_name,
                                                                                                db_password)

    compose_manager.save()
    env_manager.add_value(f'{service_name}_DB_PASSWORD', db_password)
    env_manager.save()
    copy_files_from_container('live', '/odoo/src', f'./volumes/{service_name}/src')
    click.echo(f"Development environment for PR{pr_number} added successfully.")


@manage_dev_env.command()
@click.argument('pr_number')
@click.pass_context
def remove(ctx, pr_number):
    compose_manager = ctx.obj['compose_manager']
    env_manager = ctx.obj['env_manager']
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
    DatabaseManager(DEFAULT_DB, DB_USER, env_manager.read_value('MASTER_DB_PASSWORD')).remove_user(service_name)
    env_manager.remove_value(f'{service_name}_DB_PASSWORD')
    env_manager.save()
    click.echo(f"Development environment for PR{pr_number} removed successfully.")


@manage_dev_env.command()
@click.pass_context
def remove_all(ctx):
    compose_manager = ctx.obj['compose_manager']
    if not compose_manager.initiated:
        click.echo("Please run the 'init' command before running this command.", err=True)
        exit(1)

    removed = False
    # List services to avoid "dictionary changed size during iteration" error
    for service_name in [key for key in compose_manager.services.keys() if key.startswith("odoo_dev")]:
        pr_number = service_name.split('pr')[-1]
        # Using click's context to call the remove function
        ctx = click.get_current_context()
        ctx.invoke(remove, pr_number=pr_number)
        removed = True
    if not removed:
        click.echo("No development environments found.", err=True)
        exit(4)

    click.echo("All development environments removed successfully.")
