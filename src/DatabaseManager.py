import subprocess
import uuid
import psycopg
from typing import Self

from src.errors import OperationOnDatabaseDeniedException, DatabaseAlreadyExistsException

DB_PORT = 5432

class DatabaseManager:
    def __init__(self, name: str, user: str, password: str, port: str = DB_PORT):
        self.name = name
        self.exists = self.db_exists(self.name)
        self.user = user
        self.password = password
        self.port = port

    def connect(self):
        return psycopg.connect(
            f"host=127.0.0.1 port={self.port} dbname={self.name} user={self.user} password={self.password}")

    def dump_db(self, destination_path: str) -> str:
        path = f'{destination_path}/{self.name}_{uuid.uuid4()}.dump'

        result = subprocess.run(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c', f'pg_dump -U postgres -Fc {self.name} > {path}'],
            capture_output=True, text=True)

        result.check_returncode()

        return path

    def drop_db(self) -> bool:
        if self.name == 'live':
            raise OperationOnDatabaseDeniedException('Cannot drop live database')
        result = subprocess.run(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c', f'dropdb --if-exists -U postgres {self.name}'],
            capture_output=True, text=True)

        result.check_returncode()

        self.exists = False

        return True

    def create(self) -> bool:
        if self.exists or self.db_exists(self.name):
            raise DatabaseAlreadyExistsException('Database already exists')

        self.create_db(self.name, self.user)

        self.exists = True

        return True

    @classmethod
    def from_dump(cls, name: str, user: str, password: str, path: str) -> Self:
        if cls.db_exists(name):
            raise DatabaseAlreadyExistsException('Database already exists')

        cls.create_db(name, user)
        result = subprocess.run(['docker', 'compose', 'exec', 'db', 'sh', '-c',
                                 f'pg_restore --clean --if-exists --no-acl --no-owner -d {name} -U {user} {path}'],
                                capture_output=True, text=True)

        result.check_returncode()

        return cls(name, user, password)

    @staticmethod
    def db_exists(name: str) -> bool:
        # Check if database exists but also check for other errors
        result = subprocess.run(
            ['docker', 'compose', 'exec', 'db', 'sh', '-c', f'psql -lqt | cut -d \| -f 1 | grep -qw {name}'],
            capture_output=True, text=True)

        return result.returncode == 0

    @staticmethod
    def create_db(name: str, user: str) -> bool:
        result = subprocess.run(['docker', 'compose', 'exec', 'db', 'sh', '-c', f'createdb -U {user} {name}'],
                                capture_output=True, text=True)

        result.check_returncode()

        return True
