from functools import wraps

import click
import docker

REQUIRE_INIT_ERROR_CODE = 9

from src.helper import get_service_health


def require_initiated(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not click.get_current_context().obj['compose_manager'].initiated:
            click.echo("Please run the 'init' command before running this command.", err=True)
            exit(REQUIRE_INIT_ERROR_CODE)
        return func(*args, **kwargs)

    return wrapper


def prevent_on_enviroment(disallowed_env):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if args[0] == disallowed_env:
                click.echo(f"You cannot run this command on the {disallowed_env} enviroment.", err=True)
                exit(1)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_database(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            service_health = get_service_health('db')
            if service_health != 'healthy':
                click.echo("The database service is not healthy.", err=True)
                exit(1)
        except docker.errors.NotFound:
            click.echo("The database service is not running.", err=True)
            exit(1)
        return func(*args, **kwargs)

    return wrapper
