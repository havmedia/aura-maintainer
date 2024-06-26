import copy
import os.path
import subprocess
from typing import Union

import click
import yaml

from src.Services import ComposeService
from src.errors import ServiceAlreadyExistsException, ServiceDoesNotExistException
from src.helper import display_diff


class ComposeManager:

    def __init__(self, file_path: str = 'docker-compose.yml'):
        self.initiated = False
        self.conf_path = file_path
        config = self._get_config()
        self.config = config
        self.source_config = copy.deepcopy(config)
        self.services = self.config['services']

    def _get_config(self) -> dict:
        if not os.path.exists(self.conf_path):
            return {"version": "3.8", "services": {}}  # Initialize an empty docker-compose configuration.

        with open(self.conf_path, 'r') as file:
            self.initiated = True
            config = yaml.safe_load(file)

        return config

    def save(self):
        with open(self.conf_path, 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)
        self.initiated = True

    def render(self) -> str:
        return yaml.dump(self.config, default_flow_style=False)

    def print_diff(self) -> str:
        return display_diff(yaml.dump(self.source_config, default_flow_style=False), self.render())

    def add_service(self, service: ComposeService):
        if service.name in self.services:
            raise ServiceAlreadyExistsException(f'Service {service.name} already exists.')

        self.services[service.name] = service.to_dict()

    def update_service(self, service: ComposeService):
        if service.name not in self.services:
            raise ServiceDoesNotExistException(f'Service {service.name} does not exists.')

        self.services[service.name] = service.to_dict()

    def set_service(self, service: ComposeService):
        if service.name not in self.services:
            self.add_service(service)
        else:
            self.update_service(service)

    def remove_service(self, service_name):
        if service_name not in self.services:
            raise ServiceDoesNotExistException(f'The service {service_name} does not exist.')
        del self.services[service_name]

    @staticmethod
    def up(services: Union[bool, list] = False):
        if services:
            # Only start the services specified
            command = ['docker', 'compose', 'up', '-d'] + list(services)
        else:
            # Start all services
            command = ['docker', 'compose', 'up', '-d']

        try:
            subprocess.check_call(command)
            click.echo("Services started successfully.")
            return True
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to start services: {e}", err=True)
            raise

    @staticmethod
    def stop(services: Union[bool, list] = False):
        if services:
            # Only sop the services specified
            command = ['docker', 'compose', 'stop'] + list(services)
        else:
            # Stop all services
            command = ['docker', 'compose', 'stop']

        try:
            subprocess.check_call(command)
            click.echo("Services stopped successfully.")
            return True
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to stop services: {e}", err=True)
            raise
