#!/usr/bin/env python3
"""Start the ChatVault AI backend with uvicorn."""

from __future__ import annotations

import argparse
import os

import uvicorn

from app.core.config import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chatvault",
        description=(
            "Run the ChatVault AI FastAPI backend. The React frontend is "
            "served separately from the frontend/ directory."
        ),
    )
    parser.add_argument(
        "--host",
        default=os.getenv("CHATVAULT_HOST", "127.0.0.1"),
        help="Interface to bind (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CHATVAULT_PORT", "8000")),
        help="Port to bind (default: 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for local development.",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level (default: info).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {settings.APP_VERSION}",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
