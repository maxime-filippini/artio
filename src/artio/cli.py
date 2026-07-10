import pathlib

import click

from artio import parser
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


@cli.command()
@click.argument(
    "path",
    type=click.Path(
        path_type=pathlib.Path,
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
)
def parse(path: pathlib.Path) -> None:
    with open(path) as fd:
        source = fd.read()

    out = parser.parse_workflow_definition(source, revision=1)

    if out.workflow is not None:
        click.echo("Workflow found:")
        click.echo(f"  ID: {out.workflow.name}")
        click.echo("  Nodes:")

        for node in out.workflow.nodes:
            click.echo(f"  - {node.id!r}")


if __name__ == "__main__":
    cli()
