import subprocess
import unittest
from unittest.mock import patch, MagicMock
import uuid
from src.DatabaseManager import DatabaseManager
from src.errors import DatabaseAlreadyExistsException


class TestDump(unittest.TestCase):

    def setUp(self):
        self.db_name = 'test_db'
        self.db_manager = DatabaseManager(self.db_name, 'postgres')

    @patch('uuid.uuid4')
    @patch('subprocess.run')
    def test_dump_db(self, mock_run, mock_uuid):
        # Mock UUID and subprocess

        test_uuid = uuid.UUID('1234567890abcdef1234567890abcdef')
        mock_uuid.return_value = test_uuid
        mock_run.return_value = MagicMock(returncode=0)

        expected_path = f'/destination_path/{self.db_name}_{test_uuid}.dump'
        path = self.db_manager.dump_db('/destination_path')

        mock_run.assert_called_once()
        self.assertEqual(path, expected_path)

    @patch('subprocess.run')
    def test_dump_db_error(self, mock_run):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with self.assertRaises(subprocess.CalledProcessError):
            self.db_manager.dump_db('/destination_path')


class TestFromDump(unittest.TestCase):
    def setUp(self):
        self.db_name = 'test_db'
        self.db_manager = DatabaseManager(self.db_name, 'postgres')

    @patch('subprocess.run')
    def test_from_dump(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)

        new_db_manager = DatabaseManager.from_dump('new_db', 'user', '/path/to/dump')

        mock_run.assert_called()
        self.assertIsInstance(new_db_manager, DatabaseManager)
        self.assertEqual(new_db_manager.name, 'new_db')

    @patch('subprocess.run')
    def test_from_dump_already_exists(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(DatabaseAlreadyExistsException):
            DatabaseManager.from_dump('new_db', 'user', '/path/to/dump')

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_from_dump_error(self, mock_run):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with self.assertRaises(subprocess.CalledProcessError):
            DatabaseManager.from_dump('new_db', 'user', '/path/to/dump')


class TestDropDb(unittest.TestCase):
    def setUp(self):
        self.db_name = 'test_db'
        self.db_manager = DatabaseManager(self.db_name, 'postgres')

    @patch('subprocess.run')
    def test_drop_db(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        self.assertTrue(self.db_manager.drop_db())

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_drop_live_db(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        self.db_manager.name = 'live'

        with self.assertRaises(Exception):
            self.db_manager.drop_db()

        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_drop_db_error(self, mock_run):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with self.assertRaises(subprocess.CalledProcessError):
            self.db_manager.drop_db()


class TestDbExists(unittest.TestCase):
    def setUp(self):
        self.db_name = 'test_db'
        self.db_manager = DatabaseManager(self.db_name, 'postgres')

    @patch('subprocess.run')
    def test_db_exists(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        self.assertTrue(self.db_manager.db_exists(self.db_name))

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_db_does_not_exist(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)

        self.assertFalse(self.db_manager.db_exists('new_db'))

        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_db_exists_error(self, mock_run):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with self.assertRaises(subprocess.CalledProcessError):
            self.db_manager.db_exists(self.db_name)


class TestDbCreate(unittest.TestCase):
    def setUp(self):
        self.db_name = 'test_db'
        self.db_manager = DatabaseManager(self.db_name, 'postgres')

    @patch('subprocess.run')
    @patch('src.main.DatabaseManager.db_exists')
    def test_create_db(self, mock_db_exists, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)
        mock_db_exists.return_value = False

        self.db_manager.exists = False

        self.assertTrue(self.db_manager.create())

        mock_run.assert_called_once()
        mock_db_exists.assert_called_once()

    @patch('subprocess.run')
    def test_create_db_already_exists(self, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0)

        self.db_manager.exists = True

        with self.assertRaises(DatabaseAlreadyExistsException):
            self.db_manager.create()

        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('src.main.DatabaseManager.db_exists')
    def test_create_db_already_exists_recognized_on_call(self, mock_db_exists, mock_run):
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=1)
        mock_db_exists.return_value = MagicMock(return_value=False)

        self.db_manager.exists = False

        with self.assertRaises(DatabaseAlreadyExistsException):
            self.db_manager.create()

        mock_run.assert_not_called()
        mock_db_exists.assert_called_once()

    @patch('subprocess.run')
    def test_create_db_error(self, mock_run):
        # Mock subprocess to simulate an error
        mock_run.side_effect = subprocess.CalledProcessError(1,
                                                             ['docker', 'compose', 'exec', 'db', 'sh', '-c', 'pg_dump'],
                                                             stderr='Error')

        with self.assertRaises(subprocess.CalledProcessError):
            self.db_manager.create()
