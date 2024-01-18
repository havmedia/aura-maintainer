import socket
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from src.main import get_local_ip, check_domain_and_subdomain, get_docker_versions, cli, \
    generate_password, change_domain, remove_file_in_container, escape_db, require_initiated, prevent_on_enviroment, require_database, change_domain_command

from click.testing import CliRunner


class TestMain(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch('socket.socket')
    def test_get_local_ip_successful_ip_retrieval(self, mock_socket):
        # Mock socket methods for successful connection
        mock_socket.return_value.connect.return_value = None
        mock_socket.return_value.getsockname.return_value = ["192.168.1.1"]

        ip = get_local_ip()
        self.assertEqual(ip, "192.168.1.1")

    @patch('socket.socket')
    def test_get_local_ip_failure(self, mock_socket):
        # Mock socket methods for a failed IP retrieval
        mock_socket.return_value.connect.return_value = None
        mock_socket.return_value.connect.side_effect = socket.error

        with self.assertRaises(socket.error):
            get_local_ip()

    @patch('socket.socket')
    def test_get_local_ip_socket_closed(self, mock_socket):
        # Ensure socket is closed in both scenarios
        get_local_ip()
        mock_socket.return_value.close.assert_called_once()

        mock_socket.return_value.connect.side_effect = socket.error
        with self.assertRaises(socket.error):
            get_local_ip()
        mock_socket.return_value.close.assert_called()

    @patch('src.main.get_local_ip')
    @patch('socket.gethostbyname')
    def test_check_domain_and_subdomain_both_ips_match(self, mock_gethostbyname, mock_get_local_ip):
        mock_get_local_ip.return_value = '192.168.1.1'
        mock_gethostbyname.side_effect = lambda domain: '192.168.1.1'

        result = check_domain_and_subdomain('example.com')
        self.assertTrue(result)

    @patch('src.main.get_local_ip')
    @patch('socket.gethostbyname')
    def test_check_domain_and_subdomain_ips_do_not_match(self, mock_gethostbyname, mock_get_local_ip):
        mock_get_local_ip.return_value = '192.168.1.1'
        mock_gethostbyname.side_effect = lambda domain: '192.168.1.2' if domain == 'example.com' else '192.168.1.1'

        result = check_domain_and_subdomain('example.com')
        self.assertFalse(result)

    @patch('src.main.get_local_ip')
    @patch('socket.gethostbyname')
    def test_check_domain_and_subdomain_exception_in_ip_resolution(self, mock_gethostbyname, mock_get_local_ip):
        mock_get_local_ip.return_value = '192.168.1.1'
        mock_gethostbyname.side_effect = socket.gaierror

        with self.assertRaises(socket.gaierror):
            check_domain_and_subdomain('invalid_domain.com')

    @patch('src.main.get_docker_client')
    @patch('subprocess.run')
    def test_get_docker_versions_both_versions_success(self, mock_run, mock_get_docker_client):
        # Mocking successful Docker client version retrieval
        mock_client = MagicMock()
        mock_client.version.return_value = {'Version': '20.10.7'}
        mock_get_docker_client.return_value = mock_client

        # Mocking successful Docker Compose version retrieval
        mock_run.return_value = MagicMock(stdout='docker compose version 1.29.2\n')

        docker_version, docker_compose_version = get_docker_versions()
        self.assertEqual(docker_version, '20.10.7')
        self.assertEqual(docker_compose_version, '1.29.2')

    @patch('src.main.get_docker_client')
    @patch('subprocess.run')
    def test_get_docker_versions_docker_version_fail(self, mock_run, mock_get_docker_client):
        mock_get_docker_client.side_effect = Exception
        mock_run.return_value = MagicMock(stdout='docker compose version 1.29.2\n')

        docker_version, docker_compose_version = get_docker_versions()
        self.assertIsNone(docker_version)
        self.assertEqual(docker_compose_version, '1.29.2')

    @patch('src.main.get_docker_client')
    @patch('subprocess.run')
    def test_get_docker_versions_docker_compose_version_fail(self, mock_run, mock_get_docker_client):
        mock_client = MagicMock()
        mock_client.version.return_value = {'Version': '20.10.7'}
        mock_get_docker_client.return_value = mock_client
        mock_run.side_effect = Exception

        docker_version, docker_compose_version = get_docker_versions()
        self.assertEqual(docker_version, '20.10.7')
        self.assertIsNone(docker_compose_version)

    @patch('src.main.get_docker_client')
    @patch('subprocess.run')
    def test_get_docker_versions_both_versions_fail(self, mock_run, mock_get_docker_client):
        mock_get_docker_client.side_effect = Exception
        mock_run.side_effect = Exception

        docker_version, docker_compose_version = get_docker_versions()
        self.assertIsNone(docker_version)
        self.assertIsNone(docker_compose_version)

    @patch('src.main.get_docker_versions')
    @patch('click.echo')
    def test_all_versions_present(self, mock_echo, mock_get_docker_versions):
        mock_get_docker_versions.return_value = ('20.10.7', '1.29.2')

        result = self.runner.invoke(cli)
        mock_echo.assert_not_called()
        self.assertEqual(result.exit_code, 0)


class TestGeneratePassword(unittest.TestCase):
    def test_password_length(self):
        byte_length = 10
        expected_min_length = int(byte_length * 1.3)  # Approximate minimum length after base64 encoding
        password = generate_password(byte_length)
        self.assertGreaterEqual(len(password), expected_min_length)

    def test_randomness(self):
        password1 = generate_password(10)
        password2 = generate_password(10)
        self.assertNotEqual(password1, password2)

    def test_return_type(self):
        password = generate_password(10)
        self.assertIsInstance(password, str)

class TestRemoveFileInContainer(unittest.TestCase):

    @patch('subprocess.run')
    def test_remove_file(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.return_value = None

        result = remove_file_in_container('container_name', '/path/to/file')
        self.assertTrue(result)
        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'container_name', 'sh', '-c', 'rm /path/to/file'],
            capture_output=True, text=True
        )

    @patch('subprocess.run')
    def test_remove_file_recursive(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.return_value = None

        result = remove_file_in_container('container_name', '/path/to/directory', recursive=True)
        self.assertTrue(result)
        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'container_name', 'sh', '-c', 'rm -r /path/to/directory'],
            capture_output=True, text=True
        )

    @patch('subprocess.run')
    def test_remove_file_error(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.side_effect = subprocess.CalledProcessError(1, 'cmd')

        with self.assertRaises(subprocess.CalledProcessError):
            remove_file_in_container('container_name', '/path/to/file')

        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'container_name', 'sh', '-c', 'rm /path/to/file'],
            capture_output=True, text=True
        )



class TestDecorators(unittest.TestCase):

    # Test for check_initiated decorator
    @patch('src.main.compose_manager')
    def test_require_initiated(self, mock_compose_manager):
        mock_compose_manager.initiated = False

        @require_initiated
        def dummy_function():
            return True

        with self.assertRaises(SystemExit) as cm:
            dummy_function()
        self.assertEqual(cm.exception.code, 1)

    @patch('src.main.compose_manager')
    def test_require_initiated_if_initiated(self, mock_compose_manager):
        mock_compose_manager.initiated = True

        @require_initiated
        def dummy_function():
            return True

        self.assertEqual(dummy_function(), True)

    # Test for check_not_live_environment decorator
    def test_prevent_on_enviroment(self):
        @prevent_on_enviroment('live')
        def dummy_function(environment):
            return True

        with self.assertRaises(SystemExit) as cm:
            dummy_function('live')

        self.assertEqual(cm.exception.code, 1)

    # Test for check_database_health decorator
    @patch('src.main.get_service_health')
    def test_require_database(self, mock_get_service_health):
        mock_get_service_health.return_value = 'unhealthy'

        @require_database
        def dummy_function():
            return True

        with self.assertRaises(SystemExit) as cm:
            dummy_function()
        self.assertEqual(cm.exception.code, 1)
