"""Command-line interface for Ghost EDR Enforcer."""
from __future__ import annotations

import asyncio
import signal
from pathlib import Path
from typing import TYPE_CHECKING

import click
import structlog

from ghost_enforcer.config import EnforcerConfig, load_config
from ghost_enforcer.daemon import EnforcerDaemon
from ghost_enforcer.utils.logging import setup_logging

if TYPE_CHECKING:
    pass


@click.group()
@click.version_option(version="1.0.0", prog_name="ghost-enforcer")
def main() -> int | None:
    """Ghost EDR Enforcer - Container Runtime Security Response Daemon."""
    return None


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file",
)
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"]),
    default="info",
    help="Logging level",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Don't execute actions, just log what would happen",
)
@click.option(
    "--port",
    type=int,
    default=8765,
    help="HTTP webhook receiver port",
)
def run(
    config: Path | None,
    log_level: str,
    dry_run: bool,
    port: int,
) -> None:
    """Start the Ghost EDR Enforcer daemon."""
    setup_logging(log_level)
    logger = structlog.get_logger()

    # Load configuration
    if config:
        cfg = load_config(config)
    else:
        cfg = EnforcerConfig(
            log_level=log_level,
            dry_run=dry_run,
            receiver_port=port,
        )

    if dry_run:
        cfg.dry_run = True
        logger.warning("Running in dry-run mode - no actions will be executed")

    # Override port if specified
    if port != 8765:
        cfg.receiver_port = port

    # Create and run daemon
    daemon = EnforcerDaemon(cfg)

    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_signal() -> None:
        asyncio.create_task(daemon.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    try:
        logger.info("Starting Ghost EDR Enforcer", port=cfg.receiver_port)
        loop.run_until_complete(daemon.run())
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    finally:
        loop.run_until_complete(daemon.shutdown())
        loop.close()


@main.command("detect-runtime")
def detect_runtime() -> None:
    """Detect the container runtime in use."""
    setup_logging("info")
    from ghost_enforcer.runtime.detector import detect_container_runtime

    runtime = detect_container_runtime()
    click.echo(f"Detected runtime: {runtime.name}")
    click.echo(f"Docker socket: {runtime.socket_path}")


@main.command("validate-config")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration file",
)
def validate_config(config: Path) -> None:
    """Validate a configuration file."""
    try:
        cfg = load_config(config)
        click.echo(f"Configuration valid: {config}")
        click.echo(f"  Receiver port: {cfg.receiver_port}")
        click.echo(f"  Policy count: {len(cfg.policies)}")
        click.echo(f"  Dry run: {cfg.dry_run}")
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
