import click
from .info import cli_info
from .move import cli_move
from .destroy import cli_delete
from .rename import cli_rename


@click.group(name="event")
def events():
    """Manage Joule event streams"""
    pass  # pragma: no cover


events.add_command(cli_info)
events.add_command(cli_move)
events.add_command(cli_delete)
events.add_command(cli_rename)
