import subprocess
import uuid
from unittest.mock import patch, MagicMock

import pytest

from src.DatabaseManager import DatabaseManager
from src.errors import DatabaseAlreadyExistsException


@pytest.fixture
def db_name():
    return 'test_db'


@pytest.fixture
def db_manager(db_name):
    return DatabaseManager(db_name, 'postgres', 'password')


class TestDump:

    @patch('uuid.uuid4')
    @patch('subprocess.run')
    def test_dump_db(self, mock_run, mock_uuid, db_manager, db_name):
        # Mock UUID and subprocess
        test_uuid = uuid.UUID('1234567890abcdef1234567890abcdef')
        mock_uuid.return_value = test_uuid
        mock_run.return_value = MagicMock(returncode=0)

        expected_path = f'/destination_path/{db_name}_{test_uuid}.dump'
        path = db_manager.dump_db('/destination_path')

        mock_run.assert_called_once()
        assert path == expected_path

    @patch('subprocess.run')
    def test_dump_db_error(self, mock_run, db_manager, db_name):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with pytest.raises(subprocess.CalledProcessError):
            db_manager.dump_db('/destination_path')


class TestFromDump:
    @patch('subprocess.run')
    def test_from_dump(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)

        new_db_manager = DatabaseManager.from_dump('new_db', 'user', 'password', '/path/to/dump')

        mock_run.assert_called()
        assert isinstance(new_db_manager, DatabaseManager)
        assert new_db_manager.name == 'new_db'

    @patch('subprocess.run')
    def test_from_dump_already_exists(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        with pytest.raises(DatabaseAlreadyExistsException):
            DatabaseManager.from_dump('new_db', 'user', 'password', '/path/to/dump')

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_from_dump_error(self, mock_run):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with pytest.raises(subprocess.CalledProcessError):
            DatabaseManager.from_dump('new_db', 'user', 'password', '/path/to/dump')


class TestDropDb:

    @patch('subprocess.run')
    def test_drop_db(self, mock_run, db_manager):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        assert db_manager.drop_db()

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_drop_live_db(self, mock_run, db_manager):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        db_manager.name = 'live'

        with pytest.raises(Exception):
            db_manager.drop_db()

        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_drop_db_error(self, mock_run, db_manager):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with pytest.raises(subprocess.CalledProcessError):
            db_manager.drop_db()


class TestDbExists:

    @patch('subprocess.run')
    def test_db_exists(self, mock_run, db_manager, db_name):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        assert db_manager.db_exists(db_name)

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_db_does_not_exist(self, mock_run, db_manager):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)

        assert not db_manager.db_exists('new_db')

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_db_exists_error(self, mock_run, db_manager, db_name):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with pytest.raises(subprocess.CalledProcessError):
            db_manager.db_exists(db_name)


class TestDbCreate:

    @patch('subprocess.run')
    @patch('src.main.DatabaseManager.db_exists')
    def test_create_db(self, mock_db_exists, mock_run, db_manager, db_name):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)
        mock_db_exists.return_value = False

        db_manager.exists = False

        assert db_manager.create()

        mock_run.assert_called_once()
        mock_db_exists.assert_called_once()

    @patch('subprocess.run')
    def test_create_db_already_exists(self, mock_run, db_manager, db_name):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        db_manager.exists = True

        with pytest.raises(DatabaseAlreadyExistsException):
            db_manager.create()

        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('src.main.DatabaseManager.db_exists')
    def test_create_db_already_exists_recognized_on_call(self, mock_db_exists, mock_run, db_manager):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)
        mock_db_exists.return_value = MagicMock(return_value=False)

        db_manager.exists = False

        with pytest.raises(DatabaseAlreadyExistsException):
            db_manager.create()

        mock_run.assert_not_called()
        mock_db_exists.assert_called_once()

    @patch('subprocess.run')
    def test_create_db_error(self, mock_run, db_manager):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with pytest.raises(subprocess.CalledProcessError):
            db_manager.create()


class TestDbConnect:

    @patch('src.main.psycopg.connect')
    def test_connect_with_valid_credentials(self, mock_connect, db_manager):
        mock_connect.return_value = MagicMock()

        db_manager._connect()

        mock_connect.assert_called_once()


class TestDbRunSql:

    @patch('src.DatabaseManager.DatabaseManager._connect')
    def test_execute_sql(self, mock_connect, db_manager):
        mock_connect.return_value = MagicMock()

        db_manager._run_sql_command('SELECT * FROM sale_order;')

        mock_connect.assert_called_once()


class TestAddUser:
    @patch('src.DatabaseManager.DatabaseManager._run_sql_command')
    def test_add_user(self, mock_run_sql_command, db_manager):
        mock_run_sql_command.return_value = MagicMock()

        db_manager.add_user('test_user', 'password-test-user')

        mock_run_sql_command.assert_called_once_with(
            """CREATE ROLE test_user LOGIN CREATEDB PASSWORD 'password-test-user'""", True)


class TestRemoveUser:

    @patch('src.DatabaseManager.DatabaseManager._run_sql_command')
    def test_remove_user(self, mock_run_sql_command, db_manager):
        mock_run_sql_command.return_value = MagicMock()

        db_manager.remove_user('test-user')

        mock_run_sql_command.assert_called_once_with(
            """DROP ROLE IF EXISTS test-user""", True)
