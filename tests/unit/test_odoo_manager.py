import pytest

from src.ComposeManager import ComposeManager
from src.EnvManager import EnvManager
from src.OdooManager import OdooManager
from src.errors import EnviromentAlreadyExistException


class TestOdooExists:

    def test_odoo_exists(self):
        compose_manager = ComposeManager()

        compose_manager.services = {
            'odoo_existing': {'some_conf': 'some_value'}
        }

        assert OdooManager.odoo_exists(compose_manager, 'existing') is True

    def test_odoo_not_exists(self):
        compose_manager = ComposeManager()

        compose_manager.services = {
            'odoo_existing': {'some_conf': 'some_value'}
        }

        assert OdooManager.odoo_exists(compose_manager, 'ella') is False


class TestOdooAdd:

    def test_odoo_add_already_exist(self):
        compose_manager = ComposeManager()
        env_manager = EnvManager()

        compose_manager.services = {
            'odoo_existing': {'some_conf': 'some_value'}
        }

        odoo_manager = OdooManager(compose_manager, env_manager, 'existing')

        with pytest.raises(EnviromentAlreadyExistException):
            odoo_manager.add()