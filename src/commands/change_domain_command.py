import click

from src.commands.generate_command import generate
from src.decorators import require_initiated
from src.error_codes import DOMAIN_NOT_CONFIGURED_ERROR_CODE
from src.helper import check_domain_and_subdomain


@click.command('change-domain')
@click.argument('new_domain')
@click.pass_context
def change_domain_command(ctx, new_domain):
    change_domain(new_domain, compose_manager=ctx.obj['compose_manager'], env_manager=ctx.obj['env_manager'])


@require_initiated
def change_domain(new_domain, compose_manager, env_manager):
    dev = env_manager.read_value('DEV', '0') == '1'
    if check_domain_and_subdomain(new_domain, dev):
        click.echo(
            f"Domain and subdomains must point to this server's IP. Please ensure the domain and subdomains are correctly configured.",
            err=True)
        exit(DOMAIN_NOT_CONFIGURED_ERROR_CODE)

    env_manager.update_value('DOMAIN', new_domain)
    env_manager.save()
    click.echo(f"Domain changed to {new_domain}.")

    generate(
        compose_manager=compose_manager,
        env_manager=env_manager,
    )
