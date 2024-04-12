import click

from src.Services import ProxyComposeService, OdooComposeService, PostgresComposeService, KwkhtmltopdfComposeService
from src.helper import generate_password, display_diff


@click.command('generate')
@click.option('--dashboard', is_flag=True,
              help='Enable dashboard for the proxy service. Please use this only for debug purposes.')
@click.option('--dry', is_flag=True,
              help='Runs the generation in dry mode and do not change any files.')
@click.pass_context
def generate_command(ctx, dry, dashboard):
    generate(
        dashboard=dashboard,
        dry=dry,
        compose_manager=ctx.obj['compose_manager'],
        env_manager=ctx.obj['env_manager']
    )


def generate(compose_manager, env_manager, dashboard=False, dry=False):
    if not env_manager.initiated:
        click.echo("Please run the 'init' command before generating the configuration.", err=True)
        exit(1)
    domain = env_manager.read_value('DOMAIN')
    version = env_manager.read_value('VERSION')
    is_dev = env_manager.read_value('DEV', '0') == '1'
    module_mode = env_manager.read_value('MODULE_MODE') if env_manager.read_value('MODULE_MODE') else 'included'
    # Store domain in the proxy service for later reference
    proxy_service = ProxyComposeService(name='proxy', domain=domain, dashboard=dashboard, https=not is_dev)
    live_service = OdooComposeService(name='live', domain=domain, db_password='${LIVE_DB_PASSWORD}',
                                      admin_passwd=generate_password(), odoo_version=version, basic_auth=False,
                                      https=not is_dev,
                                      module_mode=module_mode)  # Generate a random password each time because it will never be needed
    pre_service = OdooComposeService(name='pre', domain=f'pre.{domain}', db_password='${PRE_DB_PASSWORD}',
                                     admin_passwd=generate_password(), odoo_version=version, https=not is_dev,
                                     module_mode=module_mode)
    db_service = PostgresComposeService(name='db')
    kwkhtmltopdf_service = KwkhtmltopdfComposeService(name='kwkhtmltopdf')
    # Update services
    compose_manager.set_service(proxy_service)
    compose_manager.set_service(live_service)
    compose_manager.set_service(pre_service)
    compose_manager.set_service(db_service)
    compose_manager.set_service(kwkhtmltopdf_service)
    # Write Docker Compose file
    if dry:
        click.echo(compose_manager.print_diff())
        click.echo(f"Docker Compose file 'docker-compose.yml' rendered successfully.")
    else:
        compose_manager.save()
        click.echo(f"Docker Compose file 'docker-compose.yml' updated successfully.")
