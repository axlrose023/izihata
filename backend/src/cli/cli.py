import os
import subprocess
from configparser import ConfigParser
from dataclasses import asdict
from decimal import Decimal
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
from app.database.imports import (
    BunnyS3Config,
    import_eti_workbook,
    import_products,
    planned_media_urls,
    read_eti_workbook,
    read_rows,
    upload_eti_media,
)
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
    remap_categories: Annotated[
        bool,
        typer.Option(
            "--remap-categories",
            help=(
                "Re-apply category rules to products that already exist."
                " Discards category corrections made by hand."
            ),
        ),
    ] = False,
    placeholder_price: Annotated[
        str | None,
        typer.Option(
            "--placeholder-price",
            help=(
                "Import rows that carry no price using this value. Such products"
                " are always hidden until a real price is set."
            ),
        ),
    ] = None,
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
                placeholder_price=(
                    Decimal(placeholder_price)
                    if placeholder_price is not None
                    else None
                ),
                activate=activate,
                remap_categories=remap_categories,
                dry_run=not apply,
            )
            mode = "APPLIED" if apply else "DRY RUN (nothing written)"
            typer.echo(typer.style(f"\n{mode}", fg=typer.colors.CYAN, bold=True))
            typer.echo(f"rows read      : {len(rows)}")
            typer.echo(f"to create      : {outcome.created}")
            typer.echo(f"to update      : {outcome.updated}")
            typer.echo(f"skipped, no price: {len(outcome.skipped_without_price)}")
            if outcome.needs_pricing:
                typer.echo(
                    typer.style(
                        f"awaiting a real price (hidden): {outcome.needs_pricing}",
                        fg=typer.colors.YELLOW,
                    )
                )
            typer.echo(f"unmapped category: {len(outcome.unmapped)}")
            if outcome.published:
                typer.echo(
                    typer.style(
                        f"published       : {outcome.published}",
                        fg=typer.colors.GREEN,
                    )
                )
            if outcome.recategorised:
                typer.echo(f"recategorised   : {outcome.recategorised}")
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


@app.command("import-eti")
def import_eti_command(
    path: Annotated[Path, typer.Argument(help="ETI XLSX workbook")],
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Write products to the database"),
    ] = False,
    upload_media: Annotated[
        bool,
        typer.Option(
            "--upload-media",
            help="Copy the source photo sheet to Bunny Storage before importing",
        ),
    ] = False,
    endpoint: Annotated[
        str | None,
        typer.Option(
            envvar="BUNNY_S3_ENDPOINT",
            help="Bunny S3 endpoint; defaults to BUNNY_S3_ENDPOINT",
        ),
    ] = None,
    storage_zone: Annotated[
        str | None,
        typer.Option(
            envvar="BUNNY_STORAGE_ZONE",
            help="Bunny Storage zone; defaults to BUNNY_STORAGE_ZONE",
        ),
    ] = None,
    storage_password: Annotated[
        str | None,
        typer.Option(
            envvar="BUNNY_STORAGE_PASSWORD",
            help="Bunny write password; defaults to BUNNY_STORAGE_PASSWORD",
        ),
    ] = None,
    public_base_url: Annotated[
        str | None,
        typer.Option(
            envvar="BUNNY_MEDIA_PUBLIC_BASE_URL",
            help="Public Bunny Pull Zone URL; defaults to BUNNY_MEDIA_PUBLIC_BASE_URL",
        ),
    ] = None,
    concurrency: Annotated[
        int,
        typer.Option(min=1, max=32, help="Concurrent image transfers"),
    ] = 8,
) -> None:
    """Import ETI products, primary/ETIM characteristics and product images.

    The command previews data by default.  ``--apply`` imports product data;
    adding ``--upload-media`` first copies every source image into Bunny S3.
    Set the four Bunny variables in the environment instead of placing secrets
    in a command history.
    """
    if not path.exists():
        typer.echo(typer.style(f"File not found: {path}", fg=typer.colors.RED))
        raise typer.Exit(code=1)
    try:
        workbook = read_eti_workbook(path)
    except (OSError, ValueError) as error:
        typer.echo(typer.style(f"Cannot read workbook: {error}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from error

    endpoint_value = endpoint or os.getenv("BUNNY_S3_ENDPOINT")
    storage_zone_value = storage_zone or os.getenv("BUNNY_STORAGE_ZONE")
    storage_password_value = storage_password or os.getenv("BUNNY_STORAGE_PASSWORD")
    public_base_url_value = public_base_url or os.getenv("BUNNY_MEDIA_PUBLIC_BASE_URL")
    has_bunny_values = any(
        (
            endpoint_value,
            storage_zone_value,
            storage_password_value,
            public_base_url_value,
        )
    )
    if upload_media and not apply:
        typer.echo(typer.style("--upload-media requires --apply", fg=typer.colors.RED))
        raise typer.Exit(code=1)
    if (upload_media or has_bunny_values) and not all(
        (
            endpoint_value,
            storage_zone_value,
            storage_password_value,
            public_base_url_value,
        )
    ):
        typer.echo(
            typer.style(
                "Bunny configuration needs endpoint, zone, password and public URL",
                fg=typer.colors.RED,
            )
        )
        raise typer.Exit(code=1)
    config = (
        BunnyS3Config(
            endpoint=endpoint_value,
            storage_zone=storage_zone_value,
            password=storage_password_value,
            public_base_url=public_base_url_value,
        )
        if endpoint_value
        and storage_zone_value
        and storage_password_value
        and public_base_url_value
        else None
    )

    async def _run() -> None:
        media_urls = planned_media_urls(workbook, config) if config else None
        if upload_media:
            if config is None:
                raise RuntimeError("Bunny configuration unexpectedly missing")
            typer.echo("Copying ETI photos to Bunny Storage…")
            upload_outcome = await upload_eti_media(
                workbook,
                config,
                concurrency=concurrency,
            )
            media_urls = upload_outcome.public_urls
            typer.echo(f"images uploaded : {upload_outcome.uploaded}")
            typer.echo(f"images existing : {upload_outcome.already_present}")
            typer.echo(f"images failed   : {len(upload_outcome.failed)}")
            for failure in upload_outcome.failed[:10]:
                typer.echo(f"  {failure[:160]}")

        async with SessionFactory() as session:
            outcome = await import_eti_workbook(
                session,
                workbook,
                media_urls=media_urls,
                dry_run=not apply,
            )
            mode = "APPLIED" if apply else "DRY RUN (nothing written)"
            typer.echo(typer.style(f"\n{mode}", fg=typer.colors.CYAN, bold=True))
            typer.echo(f"products        : {outcome.total}")
            typer.echo(f"created         : {outcome.created}")
            typer.echo(f"updated         : {outcome.updated}")
            typer.echo(f"duplicate rows  : {workbook.duplicate_product_rows}")
            typer.echo(f"primary specs   : {outcome.primary_specifications}")
            typer.echo(f"ETIM specs      : {outcome.etim_specifications}")
            typer.echo(f"photos attached : {outcome.media_attached}")
            typer.echo(f"fallback category: {len(outcome.unmapped)}")
            for item in outcome.unmapped[:10]:
                typer.echo(f"  {item[:120]}")

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
