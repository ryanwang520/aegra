"""Command-line interface for Aegra server management."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import structlog
import uvicorn
from dotenv import load_dotenv

from .utils.setup_logging import get_logging_config, setup_logging


def _apply_default_env() -> None:
    """Set sane defaults for local usage without overriding user config."""
    if not os.getenv("AUTH_TYPE"):
        os.environ["AUTH_TYPE"] = "noop"


def _resolve_host_port(args: argparse.Namespace) -> tuple[str, int]:
    host = args.host or os.getenv("HOST", "0.0.0.0")
    port = args.port or int(os.getenv("PORT", "2024"))
    return host, port


def _run_migrations() -> int:
    root = Path(__file__).resolve().parent
    if not (root / "alembic.ini").exists():
        print("alembic.ini not found. Cannot run migrations.")
        return 1

    cmd = ["alembic", "-c", str(root / "alembic.ini"), "upgrade", "head"]
    print(f"+ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, cwd=str(root))
    except subprocess.CalledProcessError as exc:
        print(f"Migration failed with exit code {exc.returncode}.")
        return exc.returncode
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    """Start the Aegra server."""
    if args.config:
        os.environ["AEGRA_CONFIG"] = args.config

    load_dotenv()
    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL is required. Set it in the environment or .env.")
        return 1
    _apply_default_env()
    migrate_rc = _run_migrations()
    if migrate_rc != 0:
        return migrate_rc
    setup_logging()

    logger = structlog.get_logger(__name__)
    host, port = _resolve_host_port(args)

    logger.info("Starting Aegra", host=host, port=port)

    uvicorn.run(
        "agent_server.main:app",
        host=host,
        port=port,
        reload=args.reload,
        access_log=False,
        log_config=get_logging_config(),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arcsitegraph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    up_parser = subparsers.add_parser("up", help="Start the Aegra server")
    up_parser.add_argument(
        "--host",
        help="Host interface to bind (default: HOST env or 0.0.0.0)",
    )
    up_parser.add_argument(
        "--port",
        type=int,
        help="Port to bind (default: PORT env or 8000)",
    )
    up_parser.add_argument(
        "--config",
        help="Path to aegra.json or langgraph.json (sets AEGRA_CONFIG)",
    )
    up_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes",
    )
    up_parser.set_defaults(func=cmd_up)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
