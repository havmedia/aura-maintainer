import json

import click
import docker

from src.helper import get_docker_versions, check_domain_and_subdomain, get_service_health


@click.command('inspect')
@click.option('--json', 'return_json', is_flag=True, help='Output the data in JSON format', )
@click.pass_context
def inspect_command(ctx, return_json):
    inspect(return_json, compose_manager=ctx.obj['compose_manager'], env_manager=ctx.obj['env_manager'])


def inspect(return_json, compose_manager, env_manager):
    initialized = compose_manager.initiated
    domain = env_manager.read_value('DOMAIN') if initialized else 'Not initialized'
    dev = env_manager.read_value('DEV', '0') == 1
    odoo_version = env_manager.read_value('VERSION') if initialized else 'Not initialized'
    # Count the number of dev environments with the "pr_" prefix
    num_dev_envs = sum(1 for service_name in compose_manager.services.keys() if service_name.startswith("odoo_dev"))
    docker_version, docker_compose_version = get_docker_versions()
    docker_installed = docker_version is not None
    docker_compose_installed = docker_compose_version is not None
    domain_configured = check_domain_and_subdomain(domain, dev) if initialized else None
    try:
        db_health = get_service_health('db') if initialized else None
    except docker.errors.NotFound:
        db_health = None
    try:
        proxy_health = get_service_health('proxy') if initialized else None
    except docker.errors.NotFound:
        proxy_health = None
    if return_json:
        # Output data in JSON format
        data = {"state": {"initialized": initialized, "domain": domain, "odoo_version": odoo_version,
                          "num_dev_envs": num_dev_envs, "docker_version": docker_version,
                          "docker_compose_version": docker_compose_version, "db_health": db_health,
                          "proxy_health": proxy_health},
                "checklist": {"domain_configured": domain_configured, "subdomain_configured": domain_configured,
                              "docker_installed": docker_installed,
                              "docker_compose_installed": docker_compose_installed}}
        click.echo(json.dumps(data, indent=4))
    else:
        # Output data in human-readable format
        click.echo("State:")
        click.echo(f"  Initialized: {'Yes' if initialized else 'No'}")
        click.echo(f"  Domain: {domain}")
        click.echo(f"  Odoo version: {odoo_version}")
        click.echo(f"  Number of dev environments: {num_dev_envs}")
        click.echo(f"  Docker version: {docker_version}")
        click.echo(f"  Docker Compose version: {docker_compose_version}")
        click.echo(f"  Database health: {db_health}")
        click.echo(f"  Proxy health: {proxy_health}")

        click.echo("\nChecklist:")
        if initialized:
            click.echo(f"  - Domain configured: {'✓' if domain_configured else '✗'}")
            click.echo(f"  - Subdomain configured: {'✓' if domain_configured else '✗'}")
        else:
            click.echo("  - Domain configured: N/A (not initialized)")
            click.echo("  - Subdomain configured: N/A (not initialized)")
        click.echo(f"  - Docker installed: {'✓' if docker_installed else '✗'}")
        click.echo(f"  - Docker Compose installed: {'✓' if docker_compose_installed else '✗'}")
