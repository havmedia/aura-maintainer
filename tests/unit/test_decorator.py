import click
import docker
import pytest

from src import decorators
from src.decorators import require_initiated, prevent_on_enviroment, require_database
from src.errors import RequireInitializedException, CannotRunOnThisEnviromentException, RequireDatabaseServiceException


class MockDockerContainerNotFoundError:
    def __init__(self, *args, **kwargs):
        raise docker.errors.NotFound('Docker container not found')


class MockClickContext:
    def __init__(self, initiated=False):
        self.obj = {'compose_manager': ComposeManager(initiated)}


class TestDecorators:

    # Test for check_initiated decorator
    def test_require_initiated(self, monkeypatch):
        monkeypatch.setattr(click, 'get_current_context', lambda: MockClickContext())

        @require_initiated
        def dummy_function():
            return True

        with pytest.raises(RequireInitializedException):
            dummy_function()

    def test_require_initiated_if_initiated(self, monkeypatch):
        monkeypatch.setattr(click, 'get_current_context', lambda: MockClickContext(True))

        @require_initiated
        def dummy_function():
            return True

        assert dummy_function() is True

    # Test for check_not_live_environment decorator
    def test_prevent_on_enviroment(self):
        @prevent_on_enviroment('live')
        def dummy_function(environment):
            return True

        with pytest.raises(CannotRunOnThisEnviromentException):
            dummy_function('live')


    def test_prevent_on_multiple_enviroment(self):
        @prevent_on_enviroment('live', 'db', 'proxy')
        def dummy_function(environment):
            return True

        with pytest.raises(CannotRunOnThisEnviromentException):
            dummy_function('live')

        with pytest.raises(CannotRunOnThisEnviromentException):
            dummy_function('db')

    def test_prevent_on_enviroment_success(self):
        @prevent_on_enviroment('live')
        def dummy_function(environment):
            return True

        assert dummy_function('pre')

    # Test for check_database_health decorator
    def test_require_database(self, monkeypatch):
        monkeypatch.setattr(decorators, 'get_service_health', lambda _: 'unhealthy')

        @require_database
        def dummy_function():
            return True

        with pytest.raises(RequireDatabaseServiceException):
            dummy_function()

    def test_require_database_container_not_found(self, monkeypatch):
        monkeypatch.setattr(decorators, 'get_service_health', MockDockerContainerNotFoundError)

        @require_database
        def dummy_function():
            return True

        with pytest.raises(RequireDatabaseServiceException):
            dummy_function()

    def test_require_database_successfull(self, monkeypatch):
        monkeypatch.setattr(decorators, 'get_service_health', lambda _: 'healthy')

        @require_database
        def dummy_function():
            return True

        assert dummy_function()


class ComposeManager:
    def __init__(self, initiated):
        self.initiated = initiated  # the original attribute that we want to mock
