import os
import shutil
import subprocess

import pytest
from click.testing import CliRunner

from src.EnvManager import EnvManager
from src.decorators import REQUIRE_INIT_ERROR_CODE
from src.error_codes import DOMAIN_NOT_CONFIGURED_ERROR_CODE
from src.main import cli


# noinspection PyTypeChecker
class TestChangeDomainCommand:

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
                            '--dev'])  # Use dev mode to prevent ssl and https problems. Surely this never get us in trouble. /:

    def test_change_domain_successfully(self, init_setup):
        new_domain = 'newdomain.de'

        runner = CliRunner()

        result = runner.invoke(cli, ['change-domain', new_domain])

        assert result.exit_code == 0

        assert f'Domain changed to {new_domain}' in result.output
        assert 'Docker Compose file \'docker-compose.yml\' updated successfully.' in result.output

        env_manager = EnvManager()

        assert env_manager.read_value('DOMAIN') == new_domain

    def test_change_domain_fails_if_not_initialized(self, tmp_path):
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            new_domain = 'new_domain_786.de'

            runner = CliRunner()

            result = runner.invoke(cli, ['change-domain', new_domain])

            assert result.exit_code == REQUIRE_INIT_ERROR_CODE

            assert 'Please run the \'init\' command before running this command' in result.output
        finally:
            os.chdir(original_dir)

    def test_change_domain_fails_if_not_allowed_domain(self, init_setup):
        new_domain = 'new_domain_ 786.de'

        runner = CliRunner()

        result = runner.invoke(cli, ['change-domain', new_domain])

        assert result.exit_code == DOMAIN_NOT_CONFIGURED_ERROR_CODE
