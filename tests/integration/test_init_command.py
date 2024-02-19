import os
import pathlib
import shutil
import subprocess

import docker

import pytest
from click.testing import CliRunner
from docker.errors import DockerException

from src.main import cli
from src.error_codes import DOCKER_NOT_RUNNING_ERROR_CODE, DOMAIN_NOT_CONFIGURED_ERROR_CODE


@pytest.fixture(autouse=True, scope='function')
def setup_environment(tmp_path):
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    print('INIT')
    yield
    print('DEST')
    try:
        subprocess.run(['docker', 'compose', 'down'], capture_output=True, text=True)
    except Exception as e:
        print(f"Error cleaning up Docker environment: {e}")
    finally:
        shutil.rmtree(tmp_path)
        os.chdir(original_dir)  # Ensure we return to the original directory


def raise_docker_not_running() -> None:
    raise DockerException(
        "Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))")


# noinspection PyTypeChecker
class TestInitCommand:

    def test_if_command_can_be_run_successfully(self):
        runner = CliRunner()

        result = runner.invoke(cli, ['init', 'test.de', '17.0',
                                     '--dev'])  # Use dev mode to prevent ssl and https problems. Surely this never get us in trouble. /:

        # Check for successfully feedback
        assert "Docker Compose file 'docker-compose.yml' updated successfully." in result.output
        assert "Services started successfully." in result.output
        assert result.exit_code == 0

        # Check that needed files are generated
        assert os.path.exists(pathlib.Path('./.env'))
        assert os.path.exists(pathlib.Path('./docker-compose.yml'))

        # Check that all Docker Containers are running

        client = docker.from_env()

        containers = client.containers.list()

        compose_services = ['live', 'db', 'proxy', 'kwkhtmltopdf']

        for service in compose_services:
            # Check if there is a running container for each service
            assert any(service == container.name and container.status == 'running' for container in containers), \
                f"Service {service} is not running"

    def test_if_command_does_not_run_if_docker_and_compose_does_not_run(self, monkeypatch):
        # Mock Docker to simulate it is not installed
        monkeypatch.setattr(docker, 'from_env', raise_docker_not_running)

        runner = CliRunner()

        result = runner.invoke(cli, ['init'])

        assert result.exit_code == DOCKER_NOT_RUNNING_ERROR_CODE
        assert 'Docker and/or Docker Compose are not installed or running.' in result.output

    def test_if_command_does_not_run_if_domains_not_setup(self):
        runner = CliRunner()

        result = runner.invoke(cli, ['init', 'test.de', '17.0'])

        assert result.exit_code == DOMAIN_NOT_CONFIGURED_ERROR_CODE
        assert 'Domain and subdomains must point to this server\'s IP. Please ensure the domain and subdomains are correctly configured.' in result.output
