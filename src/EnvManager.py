from errors import EnvVarAlreadyExistsException, EnvVarDoesNotExistException
import os

ENV_PATH = '.env'


class EnvManager:
    def __init__(self, file_path: str = ENV_PATH):
        self.initiated = False
        self.file_path = file_path
        self.env_data = self._load_env_data()

    def _load_env_data(self):
        """Loads the environment data from the file."""
        env_data = {}
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                for line in f:
                    key, value = line.strip().split('=', 1)
                    env_data[key.upper()] = value
            self.initiated = True
        return env_data

    def read_value(self, key):
        """Returns the value of the key if it exists, else None."""
        key = key.upper()
        if key not in self.env_data:
            raise EnvVarDoesNotExistException('The key "{key}" is missing in the env file')

        return self.env_data.get(key, None)

    def add_value(self, key, value):
        """Writes a new key-value pair to the .env file."""
        key = key.upper()
        if key in self.env_data:
            raise EnvVarAlreadyExistsException('The key "{key}" already exists in the env file')
        self.env_data[key] = value

    def update_value(self, key, value):
        """Updates the value of a key in the .env file."""
        key = key.upper()
        if key not in self.env_data:
            raise EnvVarDoesNotExistException('The key "{key}" is missing in the env file')
        self.env_data[key] = value

    def remove_value(self, key):
        key = key.upper()
        if key not in self.env_data:
            raise EnvVarDoesNotExistException('The key "{key}" is missing in the env file')
        del self.env_data[key]

    def save(self):
        """Saves the in-memory data to the .env file."""
        with open(self.file_path, 'w') as f:
            f.writelines([f'{k}={v}\n' for k, v in self.env_data.items()])

        self.initiated = True
