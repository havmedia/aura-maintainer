from functools import wraps

import click
import docker

from src.errors import CannotRunOnThisEnviromentException, RequireDatabaseServiceException, RequireInitializedException
from src.helper import get_service_health


def require_initiated(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not click.get_current_context().obj['compose_manager'].initiated:
            raise RequireInitializedException()
        return func(*args, **kwargs)

    return wrapper


def prevent_on_enviroment(*disallowed_services):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if kwargs.get('enviroment') in disallowed_services or (args and args[0] in disallowed_services):
                raise CannotRunOnThisEnviromentException(f"You cannot run this command for the {', '.join(disallowed_services)} enviroments.")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_database(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            service_health = get_service_health('db')
            if service_health != 'healthy':
                raise RequireDatabaseServiceException("The database service is not healthy.")
        except docker.errors.NotFound:
            raise RequireDatabaseServiceException("The database service is not running.")
        return func(*args, **kwargs)

    return wrapper
