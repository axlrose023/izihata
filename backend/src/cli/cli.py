import subprocess
from configparser import ConfigParser
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import anyio
import bcrypt
import typer
from alembic import command
from alembic.config import Config

from app.api.modules.outbox.service import OutboxRecoveryService
from app.api.modules.users.models import User
from app.database.engine import SessionFactory
from app.database.imports import import_products, read_rows
from app.database.seed import seed_database
from app.database.uow import UnitOfWork
from app.ioc import get_async_container

app = typer.Typer()


alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    if not alembic_ini_path.exists():
        raise FileNotFoundError("alembic.ini not found")
    return Config(alembic_ini_path.as_posix())


@app.command()
def tests(
    path: Annotated[str, typer.Argument()] = "src/tests",
) -> None:
    """Run parallel tests."""

    subprocess.run(["uv", "run", "pytest", path, "-n", "auto"], check=True)


@app.command("migration")
def migration(name: Annotated[str | None, typer.Option(prompt=True)] = None) -> None:
    """Generate a new Alembic migration."""
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=name, autogenerate=True)
    typer.echo(
        typer.style(
            f"New migration '{name}' created successfully.",
            fg=typer.colors.GREEN,
        ),
    )


@app.command("migrations")
def migrations() -> None:
    """list migration files."""
    if not alembic_ini_path.exists():
        raise FileNotFoundError("alembic.ini not found")
    config = ConfigParser()
    config.read(alembic_ini_path)
    migrations_path = config.get("alembic", "script_location")
    typer.echo(f"Migration files are located in: {migrations_path}")
    migration_dir = Path(migrations_path) / "versions"
    for file in migration_dir.glob("*.py"):
        typer.echo(f"- {file}")


@app.command("upgrade")
def upgrade(revision: str = "head") -> None:
    """Upgrade the database to a specific revision."""
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)
    typer.echo(
        typer.style(
            f"Database upgraded to revision '{revision}' successfully.",
            fg=typer.colors.GREEN,
        ),
    )


@app.command("seed")
def seed() -> None:
    """Seed the reference catalog and initial promotion idempotently."""

    async def _seed() -> None:
        async with SessionFactory() as session:
            await seed_database(session)

    anyio.run(_seed)
    typer.echo(typer.style("Database seed completed.", fg=typer.colors.GREEN))


@app.command("import-products")
def import_products_command(
    path: Annotated[Path, typer.Argument(help="Supplier CSV file")],
    brand: Annotated[str, typer.Option(help="Brand every row belongs to")],
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Write to the database (default: dry run)"),
    ] = False,
    activate: Annotated[
        bool,
        typer.Option(
            "--activate",
            help="Publish confidently mapped rows instead of importing them hidden",
        ),
    ] = False,
) -> None:
    """Create or refresh products from a supplier CSV.

    Runs as a dry run unless --apply is given. Rows are matched on SKU, so
    re-running the same file only refreshes name, price and stock.
    """
    if not path.exists():
        typer.echo(typer.style(f"File not found: {path}", fg=typer.colors.RED))
        raise typer.Exit(code=1)

    rows = read_rows(path)
    if not rows:
        typer.echo(typer.style("No usable rows in the file.", fg=typer.colors.RED))
        raise typer.Exit(code=1)

    async def _run() -> None:
        async with SessionFactory() as session:
            outcome = await import_products(
                session,
                rows,
                brand=brand,
                activate=activate,
                dry_run=not apply,
            )
            mode = "APPLIED" if apply else "DRY RUN (nothing written)"
            typer.echo(typer.style(f"\n{mode}", fg=typer.colors.CYAN, bold=True))
            typer.echo(f"rows read      : {len(rows)}")
            typer.echo(f"to create      : {outcome.created}")
            typer.echo(f"to update      : {outcome.updated}")
            typer.echo(f"skipped, no price: {len(outcome.skipped_without_price)}")
            typer.echo(f"unmapped category: {len(outcome.unmapped)}")
            typer.echo("\nby category:")
            for slug, count in sorted(
                outcome.per_category.items(), key=lambda item: -item[1]
            ):
                typer.echo(f"  {count:>6}  {slug}")
            if outcome.unmapped:
                typer.echo(
                    typer.style(
                        "\nfirst unmapped rows (land in 'other', hidden):",
                        fg=typer.colors.YELLOW,
                    )
                )
                for line in outcome.unmapped[:15]:
                    typer.echo(f"  {line[:90]}")

    anyio.run(_run)


@app.command("bootstrap")
def bootstrap() -> None:
    """Apply migrations and seed required reference data."""
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, "head")
    seed()


@app.command("downgrade")
def downgrade(revision: str = "-1") -> None:
    """Downgrade the database to a specific revision."""
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    typer.echo(
        typer.style(
            f"Database downgraded to revision '{revision}' successfully.",
            fg=typer.colors.GREEN,
        ),
    )


@app.command("create-user")
def create_user(
    username: Annotated[str | None, typer.Option(prompt=True)] = None,
    password: Annotated[
        str | None,
        typer.Option(prompt=True, hide_input=True),
    ] = None,
) -> None:
    """Create a new user."""
    if username is None or password is None:
        raise typer.BadParameter("Username and password are required")
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise typer.BadParameter("Password must be between 8 characters and 72 bytes")

    async def _create_user() -> None:
        container = get_async_container()
        async with container() as request_container:
            uow = await request_container.get(UnitOfWork)
            existing = await uow.users.get_by_username(username)
            if existing is not None:
                raise typer.BadParameter("Username already exists")
            hashed_password = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(rounds=12),
            ).decode("utf-8")
            user = User(
                username=username,
                password_hash=hashed_password,
                is_active=True,
            )
            await uow.users.create(user)
            await uow.commit()
            typer.echo(f"User '{username}' created successfully.")

    anyio.run(_create_user)


@app.command("outbox-stats")
def outbox_stats() -> None:
    """Show operational outbox counts by status."""

    async def _show_stats() -> None:
        container = get_async_container()
        async with container() as request_container:
            service = await request_container.get(OutboxRecoveryService)
            stats = await service.get_stats()
            for status, count in asdict(stats).items():
                typer.echo(f"{status}: {count}")

    anyio.run(_show_stats)


@app.command("retry-dead-outbox")
def retry_dead_outbox(
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
) -> None:
    """Move a bounded number of dead outbox events back to pending."""

    async def _retry() -> None:
        container = get_async_container()
        async with container() as request_container:
            service = await request_container.get(OutboxRecoveryService)
            retried = await service.retry_dead(limit)
            typer.echo(f"Retried outbox events: {retried}")

    anyio.run(_retry)
