import click

from src.ComposeManager import ComposeManager
from src import EnvManager
from src.DatabaseManager import DatabaseManager
from src.constants import DEFAULT_DB, DB_USER, ODOO_SERVICE_PREFIX
from src.errors import EnviromentAlreadyExistException
from src.helper import generate_password


class OdooManager:
    def __init__(self, compose_manager: ComposeManager, env_manager: EnvManager, name: str):
        self.name = name
        self.service_name = self.get_service_name(name)
        self.compose_manager = compose_manager
        self.env_manager = env_manager
        self.exists = self.odoo_exists(self.compose_manager, self.name)

    @staticmethod
    def odoo_exists(compose_manager: ComposeManager, name: str) -> bool:
        if OdooManager.get_service_name(name) in compose_manager.get_services():
            return True
        return False

    @staticmethod
    def get_service_name(name: str) -> str:
        return ODOO_SERVICE_PREFIX + name

    def upgrade_modules(self, modules=None):
        # TODO: Finish upgrade function
        if modules is None:
            modules = ['all']

        module_string = '.'.join(modules)
        click.echo(f'Upgrading modules {module_string} on enviroment {self.name}')

    def add(self):
        if self.exists:
            raise EnviromentAlreadyExistException()

        master_db_password = self.env_manager.read_value('MASTER_DB_PASSWORD')

        # Add env variables
        odoo_db_password = generate_password()
        self.env_manager.add_value(f'{self.service_name}_DB_PASSWORD'.upper(), odoo_db_password)
        self.env_manager.save()

        # Add DB User
        DatabaseManager(DEFAULT_DB, DB_USER, master_db_password).add_user(self.service_name, odoo_db_password)

        # Add Service to dockercompose
        pass
