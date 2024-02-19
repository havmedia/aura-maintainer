import click

from src.ComposeManager import ComposeManager
from src.EnvManager import EnvManager
from src.helper import get_docker_versions

DB_PORT = 5432
DB_USER = 'postgres'
DEFAULT_DB = 'postgres'

DOCKER_NOT_RUNNING_ERROR_CODE = 2
DOMAIN_NOT_CONFIGURED_ERROR_CODE = 8


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


if __name__ == '__main__':
    cli()
