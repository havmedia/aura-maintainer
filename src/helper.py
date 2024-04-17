import difflib
import re
import secrets
import socket
import subprocess
import time

import click
import docker
from docker.errors import DockerException

PASSWORD_LENGTH = 32
SERVICE_READY_WAIT_TIME = 300  # 300 seconds = 5 minutes
valid_hostname_regex = r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])' \
                       r'(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]))*$'


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def check_domain_and_subdomain(domain: str, dev=False) -> bool:
    if not re.match(valid_hostname_regex, domain):
        return False

    if dev:
        return True
    try:
        local_ip = get_local_ip()
        domain_ip = socket.gethostbyname(domain)
        test_subdomain_ip = socket.gethostbyname(f'test.{domain}')
    except socket.gaierror:
        return False
    return domain_ip == local_ip and test_subdomain_ip == local_ip


def get_docker_client():
    return docker.from_env()


def get_docker_versions():
    try:
        client = get_docker_client()
        docker_version = client.version()['Version']
    except DockerException:
        docker_version = None

    try:
        docker_compose_version = \
            subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True).stdout.strip().split()[
                3].replace('v', '')
    except Exception:
        docker_compose_version = None

    return docker_version, docker_compose_version


def generate_password(length=PASSWORD_LENGTH) -> str:
    return secrets.token_urlsafe(length)


def ensure_services_healthy(service_names):
    client = get_docker_client()

    start_time = time.time()

    first_check = True

    for service_name in service_names:
        # Continue looping until the service is healthy or the timeout is reached
        while True:
            # Check if the timeout has been reached
            elapsed_time = time.time() - start_time
            if elapsed_time > SERVICE_READY_WAIT_TIME:
                click.echo(f"Timeout reached while waiting for {service_name} to become healthy.", err=True)
                exit(4)

            # Get the service
            try:
                client.containers.get(service_name)
            except docker.errors.NotFound:
                click.echo(f"The {service_name} service is not running.", err=True)
                exit(5)

            # Get the health status
            health_status = get_service_health(service_name)

            if health_status == 'healthy':
                if not first_check:
                    click.echo(f"{service_name} is now healthy.")
                break
            elif health_status == 'unhealthy':
                click.echo(f"{service_name} is unhealthy. Please check your service.", err=True)
                exit(6)

            # Sleep for a while before checking the status again
            click.echo(f"Waiting for {service_name} to become healthy...")
            first_check = False
            time.sleep(5)


def get_service_health(service_name):
    client = get_docker_client()
    # Get the service
    try:
        container = client.containers.get(service_name)
    except docker.errors.NotFound:
        click.echo(f"No service found with the name {service_name}.", err=True)
        raise

    # Get the health status
    return container.attrs.get('State', {}).get('Health', {}).get('Status')


def remove_file_in_container(container_name: str, path: str, recursive: bool = False) -> bool:
    rm_command = 'rm'

    if recursive:
        rm_command += ' -r'

    result = subprocess.run(['docker', 'compose', 'exec', container_name, 'sh', '-c', f'{rm_command} {path}'],
                            capture_output=True, text=True)

    result.check_returncode()

    return True


def copy_files_from_container(service_name: str, src_path: str, dest_path: str) -> bool:
    result = subprocess.run(['docker', 'compose', 'cp', f'{service_name}:{src_path}', dest_path],
                            capture_output=True, text=True)

    result.check_returncode()

    return True


def display_diff(string1: str, string2: str) -> str:
    output = []
    matcher = difflib.SequenceMatcher(None, string1, string2)

    green = '\x1b[38;5;16;48;5;2m'
    red = '\x1b[38;5;16;48;5;1m'
    endgreen = '\x1b[0m'
    endred = '\x1b[0m'

    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'equal':
            output.append(string1[a0:a1])
        elif opcode == 'insert':
            output.append(f'{green}{string2[b0:b1]}{endgreen}')
        elif opcode == 'delete':
            output.append(f'{red}{string1[a0:a1]}{endred}')
        elif opcode == 'replace':
            output.append(f'{green}{string2[b0:b1]}{endgreen}')
            output.append(f'{red}{string1[a0:a1]}{endred}')
    return ''.join(output)
