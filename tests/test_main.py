import socket
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from src.main import get_local_ip, check_domain_and_subdomain, get_docker_versions, cli, connect_postgres, \
    generate_password, change_domain, postgres_remove_db, dump_db, remove_file_in_container, postgres_add_db, restore_db, escape_db

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

    @patch('src.main.env_manager.read_value')
    @patch('src.main.ensure_services_healthy')
    @patch('psycopg.connect')
    def test_connect_postgres_successful_connection(self, mock_connect, mock_healthy, mock_read_env):
        mock_read_env.return_value = 'dummy_password'
        mock_healthy.return_value = True
        mock_connect.return_value = MagicMock()

        connect_postgres()

        mock_healthy.assert_called_once_with(['db'])
        mock_read_env.assert_called_once_with('MASTER_DB_PASSWORD')
        mock_connect.assert_called_once_with(
            "host=127.0.0.1 port=5432 dbname=postgres user=postgres password=dummy_password")


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


class TestChangeDomain(unittest.TestCase):

    @patch('src.main.env_manager')  # Mock the env_manager
    @patch('click.echo')  # Mock click.echo
    @patch('src.main.generate')  # Mock the generate command
    def test_change_domain(self, mock_generate, mock_echo, mock_env_manager):
        runner = CliRunner()
        new_domain = "example.com"
        result = runner.invoke(change_domain, [new_domain])

        # Assertions...
        self.assertEqual(result.exit_code, 0)
        mock_env_manager.update_value.assert_called_once_with('DOMAIN', new_domain)
        mock_env_manager.save.assert_called_once()
        mock_generate.assert_called_once()


class TestPostgresRemoveDB(unittest.TestCase):

    def test_remove_live_db(self):
        with self.assertRaises(SystemExit) as e:
            postgres_remove_db('live')
            self.assertEqual(e.exception.code, 1)

    @patch('src.main.connect_postgres')
    def test_successful_db_removal(self, mock_connect_postgres):
        mock_conn = MagicMock()
        mock_connect_postgres.return_value.__enter__.return_value = mock_conn

        assert postgres_remove_db('test_db') is True

        mock_conn.execute.assert_called_once_with('DROP DATABASE IF EXISTS test_db')

    @patch('src.main.connect_postgres')
    def test_failed_db_removal(self, mock_connect_postgres):
        mock_connect_postgres.return_value.__enter__.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception) as context:
            postgres_remove_db('test_db')

        self.assertTrue("Connection failed" in str(context.exception))


class TestDumpDb(unittest.TestCase):

    @patch('subprocess.run')
    @patch('uuid.uuid4')
    def test_dump_db(self, mock_uuid4, mock_subprocess_run):
        mock_uuid4.return_value = '1234'
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.return_value = None

        expected_path = '/destination/db_name_1234.dump'
        actual_path = dump_db('db_name', '/destination')

        assert actual_path == expected_path
        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c',
             'pg_dump -U postgres -Fc db_name > /destination/db_name_1234.dump'],
            capture_output=True, text=True
        )
        mock_result.check_returncode.assert_called_once()

    @patch('subprocess.run')
    @patch('uuid.uuid4')
    def test_dump_db_error(self, mock_uuid4, mock_subprocess_run):
        mock_uuid4.return_value = '1234'
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.side_effect = subprocess.CalledProcessError(1, 'cmd')

        with self.assertRaises(subprocess.CalledProcessError):
            dump_db('db_name', '/destination')

        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c',
             'pg_dump -U postgres -Fc db_name > /destination/db_name_1234.dump'],
            capture_output=True, text=True
        )


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


class TestPostgresAddDb(unittest.TestCase):

    @patch('click.echo')
    def test_add_live_db(self, mock_click_echo):
        with self.assertRaises(SystemExit) as e:
            postgres_add_db('LIVE', 'user')
        self.assertEqual(e.exception.code, 1)
        mock_click_echo.assert_called_with("Cannot create the live database manually.", err=True)

    @patch('src.main.connect_postgres')
    def test_successful_db_creation(self, mock_connect_postgres):
        mock_conn = MagicMock()
        mock_connect_postgres.return_value.__enter__.return_value = mock_conn

        result = postgres_add_db('test_db', 'user')
        self.assertTrue(result)
        mock_conn.execute.assert_called_once_with("CREATE DATABASE test_db OWNER user")

    @patch('src.main.connect_postgres')
    @patch('click.echo')
    def test_failed_db_creation(self, mock_click_echo, mock_connect_postgres):
        mock_connect_postgres.return_value.__enter__.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception) as context:
            postgres_add_db('test_db', 'user')

        self.assertTrue("Connection failed" in str(context.exception))
        mock_click_echo.assert_called_with("Failed to remove database test_db: Connection failed", err=True)


class TestRestoreDb(unittest.TestCase):

    @patch('subprocess.run')
    def test_restore_db_success(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.return_value = None

        result = restore_db('test_db', 'user', '/path/to/dump/file')
        self.assertTrue(result)
        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c',
             'pg_restore --clean --if-exists --no-acl --no-owner -d test_db -U user /path/to/dump/file'],
            capture_output=True, text=True
        )

    @patch('subprocess.run')
    def test_restore_db_failure(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_subprocess_run.return_value = mock_result
        mock_result.check_returncode.side_effect = subprocess.CalledProcessError(1, 'cmd')

        with self.assertRaises(subprocess.CalledProcessError):
            restore_db('test_db', 'user', '/path/to/dump/file')

        mock_subprocess_run.assert_called_once_with(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c',
             'pg_restore --clean --if-exists --no-acl --no-owner -d test_db -U user /path/to/dump/file'],
            capture_output=True, text=True
        )