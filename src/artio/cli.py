import pathlib

import click

from artio.workspace import Workspace
from artio.workspace import WorkspaceAlreadyInitializedError


@click.group()
def cli():
    pass


@cli.command()
@click.argument(
    "path",
    type=click.Path(path_type=pathlib.Path),
    default=pathlib.Path.cwd(),
)
def init(path: pathlib.Path) -> None:
    """Create a new Artio workspace at PATH."""
    try:
        workspace = Workspace.initialize(path)
    except (WorkspaceAlreadyInitializedError, NotADirectoryError) as error:
        raise click.ClickException(str(error)) from error

    click.echo(f"Initialized Artio workspace at {workspace.path}")
    click.echo(f"  {workspace.manifest_path.name}")
    click.echo(f"  {workspace.workflow_path.name}")


if __name__ == "__main__":
    cli()
