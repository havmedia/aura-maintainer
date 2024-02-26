import click

from src.ComposeManager import ComposeManager
from src.EnvManager import EnvManager
from src.commands.generate_command import generate
from src.decorators import require_initiated
from src.helper import copy_files_from_container


@click.command('mount-modules')
@click.pass_context
def command_mount_modules(ctx):
    mount_modules(compose_manager=ctx.obj['compose_manager'], env_manager=ctx.obj['env_manager'])


@require_initiated
def mount_modules(compose_manager: ComposeManager, env_manager: EnvManager):
    current_mode = env_manager.read_value('MODULE_MODE', 'included')

    if current_mode == 'mounted':
        click.echo("Modules already mounted")
        exit(1)

    if current_mode is None:
        env_manager.add_value('MODE', 'mounted')

    env_manager.save()

    # Copy files for each container
    copy_files_from_container('live', '/odoo/src/', './volumes/live/src')
    copy_files_from_container('pre', '/odoo/src/', './volumes/pre/src')

    for service_name in [key for key in compose_manager.services.keys() if key.startswith("odoo_dev")]:
        copy_files_from_container(service_name, '/odoo/src/', f'./volumes/{service_name}/src')

    click.echo("Mounted modules.")

    ctx = click.get_current_context()
    ctx.invoke(generate)

    compose_manager.up()
