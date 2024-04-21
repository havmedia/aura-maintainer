import click
import docker
import pytest

from src import decorators
from src.decorators import require_initiated, REQUIRE_INIT_ERROR_CODE, prevent_on_enviroment, require_database


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

        with pytest.raises(SystemExit) as cm:
            dummy_function()
        assert cm.value.code == REQUIRE_INIT_ERROR_CODE

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

        with pytest.raises(SystemExit) as cm:
            dummy_function('live')

        assert cm.value.code == 1

    def test_prevent_on_multiple_enviroment(self):
        @prevent_on_enviroment('live', 'db', 'proxy')
        def dummy_function(environment):
            return True

        with pytest.raises(SystemExit) as cm:
            dummy_function('live')

        assert cm.value.code == 1

        with pytest.raises(SystemExit) as cm:
            dummy_function('db')

        assert cm.value.code == 1

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

        with pytest.raises(SystemExit) as cm:
            dummy_function()
        assert cm.value.code == 1

    def test_require_database_container_not_found(self, monkeypatch):
        monkeypatch.setattr(decorators, 'get_service_health', MockDockerContainerNotFoundError)

        @require_database
        def dummy_function():
            return True

        with pytest.raises(SystemExit) as cm:
            dummy_function()
        assert cm.value.code == 1

    def test_require_database_successfull(self, monkeypatch):
        monkeypatch.setattr(decorators, 'get_service_health', lambda _: 'healthy')

        @require_database
        def dummy_function():
            return True

        assert dummy_function()


class ComposeManager:
    def __init__(self, initiated):
        self.initiated = initiated  # the original attribute that we want to mock
