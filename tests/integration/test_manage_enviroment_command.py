import os
import shutil
import subprocess
from unittest import TestCase

import pytest
from click.testing import CliRunner

from src.errors import CannotRunOnThisEnviromentException
from src.main import cli


class TestManageEnviromentCommand:
    @pytest.fixture(scope="class")
    def setup_environment(self, tmp_path_factory):
        tmp_path = tmp_path_factory.mktemp(self.__class__.__name__)
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        yield
        try:
            subprocess.run(['docker', 'compose', 'down'], capture_output=True, text=True)
        except Exception as e:
            print(f"Error cleaning up Docker environment: {e}")
        finally:
            subprocess.run(['sudo', 'chmod', '-R', '777', '.'])
            shutil.rmtree(tmp_path)
            os.chdir(original_dir)  # Ensure we return to the original directory

    @pytest.fixture(scope='class')
    def init_setup(self, setup_environment):
        runner = CliRunner()

        runner.invoke(cli, ['init', 'test.de', '17.0',
                            '--dev'])  # Use dev

    def test_add_live_env(self, init_setup):
        runner = CliRunner()

        result = runner.invoke(cli, ['manage-enviroment', 'add', 'live'])

        assert isinstance(result.exception, CannotRunOnThisEnviromentException)
