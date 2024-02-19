import time

import click

from src.DatabaseManager import DatabaseManager
from src.helper import check_domain_and_subdomain, generate_password

from src.main import cli, DOMAIN_NOT_CONFIGURED_ERROR_CODE, DEFAULT_DB, DB_USER
from src.commands.generate_command import generate


@cli.command('init')
@click.argument('domain')
@click.argument('version')
@click.option('--dev', '-d', is_flag=True, help='Enable development mode. No https and other dev related things')
@click.pass_context
def init_command(ctx, domain, version, dev):
    init(dev, domain, version, ctx.obj['compose_manager'], ctx.obj['env_manager'])


def init(dev, domain, version, compose_manager, env_manager):
    # Check if .env file already exists
    if compose_manager.initiated:
        click.echo("Configuration has already been initialized.", err=True)
        exit(1)
    # Check if domain and subdomains point to the current server
    if check_domain_and_subdomain(domain, dev):
        click.echo(
            f"Domain and subdomains must point to this server's IP. Please ensure the domain and subdomains are correctly configured.",
            err=True)
        exit(DOMAIN_NOT_CONFIGURED_ERROR_CODE)
    # TODO: Check if we have access to images
    master_db_password = generate_password()
    live_db_password = generate_password()
    pre_db_password = generate_password()
    # Save data to .env file
    env_manager.add_value('DEV', '1' if dev else '0')
    env_manager.add_value('MODULE_MODE', 'included')
    env_manager.add_value('DOMAIN', domain)
    env_manager.add_value('VERSION', version)
    env_manager.add_value('MASTER_DB_PASSWORD', master_db_password)
    env_manager.add_value('LIVE_DB_PASSWORD', live_db_password)
    env_manager.add_value('PRE_DB_PASSWORD', pre_db_password)
    env_manager.save()
    click.echo('Setup initialized successfully.')
    # Run generate command
    generate(
        compose_manager=compose_manager,
        env_manager=env_manager,
    )
    compose_manager.up(['db'])

    time.sleep(5)

    DatabaseManager(DEFAULT_DB, DB_USER, master_db_password).add_user('live', live_db_password)
    DatabaseManager(DEFAULT_DB, DB_USER, master_db_password).add_user('pre', pre_db_password)
    compose_manager.up()
