import click

from src.constants import PROTECTED_SERVICES
from src.decorators import prevent_on_enviroment, require_initiated
from src.errors import EnviromentAlreadyExistException, EnviromentNotExistException


@click.group()
@require_initiated
def manage_enviroment():
    pass


@manage_enviroment.command('add')
@click.argument('enviroment')
@prevent_on_enviroment(*PROTECTED_SERVICES)
@click.pass_context
def add(ctx, enviroment):
    click.echo('Add enviroment')

    compose_manager = ctx.obj['compose_manager']

    if 'odoo_' + enviroment in compose_manager.get_services():
        raise EnviromentAlreadyExistException()


@manage_enviroment.command('remove')
@click.argument('enviroment')
@prevent_on_enviroment(*PROTECTED_SERVICES)
@click.pass_context
def remove(ctx, enviroment):
    click.echo('Remove enviroment')

    compose_manager = ctx.obj['compose_manager']

    if 'odoo_' + enviroment not in compose_manager.get_services():
        raise EnviromentNotExistException()


@manage_enviroment.command('list')
@click.pass_context
def lists(ctx):
    click.echo('list')

    services = ctx.obj['compose_manager'].get_services()

    click.echo('The following enviroments are available: ' + ', '.join(
        [service for service in services if service.startswith('odoo_')]))
