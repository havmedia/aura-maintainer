import os
import shutil
import uuid

import click

from src.DatabaseManager import DatabaseManager
from src.EnvManager import EnvManager
from src.decorators import require_initiated, require_database, prevent_on_enviroment
from src.helper import remove_file_in_container

from src.constants import DB_USER, DEFAULT_DB


@click.command('refresh-enviroment')
@click.argument('enviroment')
@click.pass_context
def refresh_enviroment_cli(ctx, enviroment):
    refresh_enviroment(enviroment, ctx.obj['compose_manager'], ctx.obj['env_manager'])


def escape_db(name: str, env_manager: EnvManager) -> bool:
    if name.lower() == 'live':
        click.echo("Cannot escape the live database manually.", err=True)
        exit(1)

    escape_statements = {'fetchmail_server': 'DELETE FROM fetchmail_server;',
                         'ir_mail_server': 'DELETE FROM ir_mail_server;',
                         'ir_cron': 'UPDATE ir_cron SET active = FALSE;',
                         'ir_config_parameter': f"UPDATE ir_config_parameter SET value = '{uuid.uuid4()}' WHERE key = 'database.uuid';"}

    main_database_manager = DatabaseManager(DEFAULT_DB, DB_USER, env_manager.read_value('MASTER_DB_PASSWORD'))

    def table_exists(table_name):
        query = f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}');"
        cur = main_database_manager._run_sql_command(query, True)
        return cur.fetchone()[0]

    try:
        for table, escape_statement in escape_statements.items():
            if not table_exists(table):
                click.echo(f"Table {table} does not exist. Skipping...", err=True)
                continue
            main_database_manager._run_sql_command(escape_statement, True)
        return True
    except Exception as e:
        click.echo(f"Failed to escape database {name}: {e}", err=True)
        raise


@require_initiated
@require_database
@prevent_on_enviroment('live')
def refresh_enviroment(enviroment, compose_manager, env_manager):
    db_password = env_manager.read_value('MASTER_DB_PASSWORD')

    if enviroment != 'pre':
        # Check if the environment exists
        if enviroment not in compose_manager.services.keys() or not enviroment.startswith('odoo'):
            click.echo(f"The environment {enviroment} does not exist or isn't an odoo env.", err=True)
            exit(1)
    click.echo(f"Refreshing {enviroment} environment")
    click.echo("* Stopping environment")
    compose_manager.stop([enviroment])
    click.echo("* Removing old database")
    DatabaseManager(enviroment, 'postgres', db_password).drop_db()
    click.echo("* Copy new database")
    path = DatabaseManager('live', 'postgres', db_password).dump_db('/tmp')
    click.echo('* Restore dump')
    enviroment_db_password = env_manager.read_value(f'{enviroment}_DB_PASSWORD'.upper())
    DatabaseManager.from_dump(enviroment, enviroment, enviroment_db_password, path)
    click.echo('* Remove dump')
    remove_file_in_container('db', path)
    click.echo('* Copy Filestore')
    enviroment_folder_path = f'volumes/{enviroment}/filestore/pre'
    live_folder_path = 'volumes/live/filestore/live'
    if os.path.exists(enviroment_folder_path):
        shutil.rmtree(enviroment_folder_path)
    shutil.copytree(live_folder_path, enviroment_folder_path)
    click.echo('* Escape new DB')
    escape_db(enviroment, env_manager=env_manager)
    click.echo("* Starting environment")
    compose_manager.up([enviroment])
