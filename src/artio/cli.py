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
@click.option("--force", is_flag=True)
def init(path: pathlib.Path, force: bool) -> None:
    """Create a new Artio workspace at PATH."""

    try:
        workspace = Workspace.initialize(path, force=force)
    except (NotADirectoryError, WorkspaceAlreadyInitializedError) as error:
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
    """Display parsed Workflow artifacts and Diagnostics from PATH."""
    source = path.read_text(encoding="utf-8")

    result = parser.parse_workflow_definition(source, revision=1)

    if result.workflow is not None:
        click.echo("Workflow found:")
        click.echo(f"  ID: {result.workflow.name}")
        click.echo("  Nodes:")

        for node in result.workflow.nodes:
            click.echo(f"  - {node.id!r} ({node.kind})")

        click.echo("  Edges:")
        for edge in result.workflow.edges:
            click.echo(f"  - {edge.source_id!r} -> {edge.target_id!r}")

    if result.fixtures:
        click.echo("Fixtures:")
        for fixture in result.fixtures:
            click.echo(f"  - {fixture.id!r}: {fixture.path!r}")

    if result.diagnostics:
        click.echo("Diagnostics:")
        for diagnostic in result.diagnostics:
            click.echo(
                "  - "
                f"{diagnostic.severity.value} "
                f"{diagnostic.code.value}: {diagnostic.message}"
            )


if __name__ == "__main__":
    cli()
