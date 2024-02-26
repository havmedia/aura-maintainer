import click

from src.ComposeManager import ComposeManager
from src.EnvManager import EnvManager
from src.commands import change_domain_command, init_command, generate_command, inspect_command, mount_modules_command, \
    refresh_enviroment_command
from src.error_codes import DOCKER_NOT_RUNNING_ERROR_CODE
from src.helper import get_docker_versions


@click.group()
@click.pass_context
def cli(ctx):
    # Check if Docker is installed & running
    docker_version, compose_version = get_docker_versions()
    if docker_version is None or compose_version is None:
        click.echo("Docker and/or Docker Compose are not installed or running.", err=True)
        exit(DOCKER_NOT_RUNNING_ERROR_CODE)

    ctx.obj = {
        'compose_manager': ComposeManager(),
        'env_manager': EnvManager(),
    }


cli.add_command(init_command.init_command)
cli.add_command(change_domain_command.change_domain_command)
cli.add_command(generate_command.generate_command)
cli.add_command(inspect_command.inspect_command)
# cli.add_command(manage_dev_env_command.command_)
cli.add_command(mount_modules_command.command_mount_modules)
cli.add_command(refresh_enviroment_command.refresh_enviroment_cli)

if __name__ == '__main__':
    cli()
