import click

from src.constants import PROTECTED_SERVICES
from src.decorators import prevent_on_enviroment


@click.group()
def manage_enviroment():
    pass


@manage_enviroment.command('add')
@click.argument('enviroment')
@prevent_on_enviroment(*PROTECTED_SERVICES)
@click.pass_context
def add(ctx, enviroment):
    click.echo('Add new enviroment')
    click.echo(enviroment)


@manage_enviroment.command('remove')
@click.argument('enviroment')
@prevent_on_enviroment(*PROTECTED_SERVICES)
@click.pass_context
def add(ctx, enviroment):
    click.echo('Remove new enviroment')
    click.echo(ctx.obj)


@manage_enviroment.command('list')
@click.pass_context
def list(ctx):
    click.echo('list')
