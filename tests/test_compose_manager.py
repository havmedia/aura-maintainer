import subprocess
import unittest
from unittest.mock import patch, mock_open, MagicMock
from src.ComposeManager import ComposeManager
from src.Services import ComposeService
from src.errors import ServiceAlreadyExistsException, ServiceDoesNotExistException

MOCK_FILE='version: \'3.8\'\nservices:\n  test_service:\n    image: \'test_image\''

class TestComposeManager(unittest.TestCase):

    def setUp(self):
        self.mock_file = mock_open(read_data=MOCK_FILE)
        self.service = ComposeService('test_service', 'test_image')

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_FILE)
    def test_init_with_existing_file(self, mock_file, mock_exists):
        manager = ComposeManager()
        self.assertTrue(manager.initiated)
        self.assertIn('test_service', manager.services)

    @patch('os.path.exists', return_value=False)
    def test_init_without_existing_file(self, mock_exists):
        manager = ComposeManager()
        self.assertFalse(manager.initiated)
        self.assertEqual(manager.config, {"version": "3.8", "services": {}})

    @patch('builtins.open', new_callable=mock_open)
    def test_save(self, mock_file):
        manager = ComposeManager()
        manager.save()
        self.assertTrue(manager.initiated)
        mock_file.assert_called_once_with('docker-compose.yml', 'w')

    def test_add_service(self):
        manager = ComposeManager()
        new_service = ComposeService('new_service', 'new_image')
        manager.add_service(new_service)
        self.assertIn('new_service', manager.services)

        with self.assertRaises(ServiceAlreadyExistsException):
            manager.add_service(new_service)

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_FILE)
    def test_update_service(self, mock_file, mock_exists):
        manager = ComposeManager()
        updated_service = ComposeService('test_service', 'updated_image')
        manager.update_service(updated_service)
        self.assertEqual(manager.services['test_service']['image'], 'updated_image')

        new_service = ComposeService('nonexistent_service', 'new_image')
        with self.assertRaises(ServiceDoesNotExistException):
            manager.update_service(new_service)

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_FILE)
    def test_remove_service(self, mock_file, mock_exists):
        manager = ComposeManager()
        manager.remove_service('test_service')
        self.assertNotIn('test_service', manager.services)

        with self.assertRaises(ServiceDoesNotExistException):
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
        with self.assertRaises(subprocess.CalledProcessError):
            manager.up()
        mock_click.assert_called_with("Failed to start services: Command 'cmd' returned non-zero exit status 1.", err=True)

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

if __name__ == '__main__':
    unittest.main()
