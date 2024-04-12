import subprocess
from unittest.mock import patch, mock_open, MagicMock

import pytest

from src.ComposeManager import ComposeManager
from src.Services import ComposeService
from src.errors import ServiceAlreadyExistsException, ServiceDoesNotExistException

MOCK_FILE = 'version: \'3.8\'\nservices:\n  test_service:\n    image: \'test_image\''


class TestComposeManager:

    def setUp(self):
        self.mock_file = mock_open(read_data=MOCK_FILE)
        self.service = ComposeService('test_service', 'test_image')

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_FILE)
    def test_init_with_existing_file(self, mock_file, mock_exists):
        manager = ComposeManager()
        assert manager.initiated
        assert 'test_service' in manager.services

    @patch('os.path.exists', return_value=False)
    def test_init_without_existing_file(self, mock_exists):
        manager = ComposeManager()
        assert not manager.initiated
        assert manager.config == {"version": "3.8", "services": {}}

    @patch('builtins.open', new_callable=mock_open)
    def test_save(self, mock_file):
        manager = ComposeManager()
        manager.save()
        assert manager.initiated
        mock_file.assert_called_once_with('docker-compose.yml', 'w')

    @patch('builtins.open', new_callable=mock_open)
    def test_render(self, mock_file):
        manager = ComposeManager()
        manager.render()
        assert not mock_file.called

    @patch('builtins.open', new_callable=mock_open)
    def test_print_diff(self, mock_file):
        manager = ComposeManager()
        manager.render()
        assert not mock_file.called


    def test_add_service(self):
        manager = ComposeManager()
        new_service = ComposeService('new_service', 'new_image')
        manager.add_service(new_service)
        assert 'new_service' in manager.services

        with pytest.raises(ServiceAlreadyExistsException):
            manager.add_service(new_service)

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_FILE)
    def test_update_service(self, mock_file, mock_exists):
        manager = ComposeManager()
        updated_service = ComposeService('test_service', 'updated_image')
        manager.update_service(updated_service)
        assert manager.services['test_service']['image'] == 'updated_image'

        new_service = ComposeService('nonexistent_service', 'new_image')
        with pytest.raises(ServiceDoesNotExistException):
            manager.update_service(new_service)

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_FILE)
    def test_remove_service(self, mock_file, mock_exists):
        manager = ComposeManager()
        manager.remove_service('test_service')
        assert 'test_service' not in manager.services

        with pytest.raises(ServiceDoesNotExistException):
            manager.remove_service('test_service')

    @patch('subprocess.check_call', return_value=0)
    @patch('click.echo')
    def test_up_with_services(self, mock_click, mock_subprocess):
        manager = ComposeManager()
        manager.up(services=['test_service'])
        mock_subprocess.assert_called_with(['docker', 'compose', 'up', '-d', 'test_service'])
        mock_click.assert_called_with("Services started successfully.")

    @patch('subprocess.check_call', return_value=0)
    @patch('click.echo')
    def test_up_without_services(self, mock_click, mock_subprocess):
        manager = ComposeManager()
        manager.up()
        mock_subprocess.assert_called_with(['docker', 'compose', 'up', '-d'])
        mock_click.assert_called_with("Services started successfully.")

    @patch('subprocess.check_call', side_effect=subprocess.CalledProcessError(1, 'cmd'))
    @patch('click.echo')
    def test_up_failure(self, mock_click, mock_subprocess):
        manager = ComposeManager()
        with pytest.raises(subprocess.CalledProcessError):
            manager.up()
        mock_click.assert_called_with("Failed to start services: Command 'cmd' returned non-zero exit status 1.",
                                      err=True)

    @patch('subprocess.check_call', return_value=0)
    @patch('click.echo')
    def test_stop_with_services(self, mock_click, mock_subprocess):
        manager = ComposeManager()
        manager.stop(services=['test_service'])
        mock_subprocess.assert_called_with(['docker', 'compose', 'stop', 'test_service'])
        mock_click.assert_called_with("Services stopped successfully.")

    @patch('subprocess.check_call', return_value=0)
    @patch('click.echo')
    def test_stop_without_services(self, mock_click, mock_subprocess):
        manager = ComposeManager()
        manager.stop()
        mock_subprocess.assert_called_with(['docker', 'compose', 'stop'])
        mock_click.assert_called_with("Services stopped successfully.")

    @patch('subprocess.check_call', side_effect=subprocess.CalledProcessError(1, 'cmd'))
    @patch('click.echo')
    def test_stop_failure(self, mock_click, mock_subprocess):
        manager = ComposeManager()
        with pytest.raises(subprocess.CalledProcessError):
            manager.stop()
        mock_click.assert_called_with("Failed to stop services: Command 'cmd' returned non-zero exit status 1.",
                                      err=True)

    def test_set_service_new_service(self):
        # Test adding a new service using set_service
        service = ComposeService(name="new_service", image="new_image")
        manager = ComposeManager()
        manager.add_service = MagicMock()
        manager.update_service = MagicMock()
        manager.services = {}  # Ensure it's empty for the test

        manager.set_service(service)

        manager.add_service.assert_called_with(service)
        manager.update_service.assert_not_called()

    def test_set_service_existing_service(self):
        # Test updating an existing service using set_service
        service = ComposeService(name="existing_service", image="new_image")
        manager = ComposeManager()
        manager.add_service = MagicMock()
        manager.update_service = MagicMock()
        manager.services = {"existing_service": service}

        manager.set_service(service)

        manager.add_service.assert_not_called()
        manager.update_service.assert_called_with(service)
