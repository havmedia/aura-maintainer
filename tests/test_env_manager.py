import unittest
from unittest.mock import patch, mock_open

from src.EnvManager import EnvManager
from src.errors import EnvVarAlreadyExistsException, EnvVarDoesNotExistException

READ_DATA = "TEST_KEY=TEST_VALUE\nANOTHER_KEY=ANOTHER_VALUE"


class TestEnvManager(unittest.TestCase):

    def setUp(self):
        self.mock_env_data = READ_DATA

    @patch('builtins.open', new_callable=mock_open, read_data=READ_DATA)
    @patch('os.path.exists', return_value=True)
    def test_load_env_data(self, mock_file, mock_exists):
        manager = EnvManager()
        print(manager.env_data)
        self.assertIn('TEST_KEY', manager.env_data)
        self.assertEqual(manager.env_data['TEST_KEY'], 'TEST_VALUE')
        self.assertTrue(manager.initiated)

    @patch('builtins.open', new_callable=mock_open, read_data=READ_DATA)
    @patch('os.path.exists', return_value=True)
    def test_read_value(self, mock_file, mock_exists):
        manager = EnvManager()
        self.assertEqual(manager.read_value('TEST_KEY'), 'TEST_VALUE')
        with self.assertRaises(EnvVarDoesNotExistException):
            manager.read_value('MISSING_KEY')

    @patch('builtins.open', new_callable=mock_open, read_data=READ_DATA)
    @patch('os.path.exists', return_value=True)
    def test_add_value(self, mock_file, mock_exist):
        manager = EnvManager()
        with self.assertRaises(EnvVarAlreadyExistsException):
            manager.add_value('TEST_KEY', 'NEW_VALUE')
        manager.add_value('NEW_KEY', 'NEW_VALUE')
        self.assertEqual(manager.env_data['NEW_KEY'], 'NEW_VALUE')

    @patch('builtins.open', new_callable=mock_open, read_data=READ_DATA)
    @patch('os.path.exists', return_value=True)
    def test_update_value(self, mock_file, mock_exists):
        manager = EnvManager()
        manager.update_value('TEST_KEY', 'UPDATED_VALUE')
        self.assertEqual(manager.env_data['TEST_KEY'], 'UPDATED_VALUE')
        with self.assertRaises(EnvVarDoesNotExistException):
            manager.update_value('MISSING_KEY', 'MISSING_VALUE')

    @patch('builtins.open', new_callable=mock_open, read_data=READ_DATA)
    @patch('os.path.exists', return_value=True)
    def test_remove_value(self, mock_file, mock_exists):
        manager = EnvManager()
        manager.remove_value('TEST_KEY')
        with self.assertRaises(EnvVarDoesNotExistException):
            manager.remove_value('MISSING_KEY')
        self.assertNotIn('TEST_KEY', manager.env_data)

    @patch('builtins.open', new_callable=mock_open)
    def test_save(self, mock_file):
        manager = EnvManager()
        manager.env_data = {'TEST_KEY': 'TEST_VALUE', 'ANOTHER_KEY': 'ANOTHER_VALUE'}
        manager.save()
        print(mock_file().writelines.call_args_list)
        mock_file().writelines.assert_any_call(['TEST_KEY=TEST_VALUE\n', 'ANOTHER_KEY=ANOTHER_VALUE\n'])

if __name__ == '__main__':
    unittest.main()
