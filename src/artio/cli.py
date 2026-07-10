import pathlib

import click

from artio.config import ArtioConfig


@click.group()
def cli():
    pass


@cli.command()
@click.argument("path", type=click.Path(), default=pathlib.Path.cwd())
def init(path: pathlib.Path):
    click.echo(path)

    cfg = ArtioConfig()

    # Check if workspace exists


if __name__ == "__main__":
    cli()
