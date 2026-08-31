"""claims-azure CLI entry point.

Phase 0 ships the skeleton. Later phases attach subcommands via lazy
imports: Phase 2 adds `generate`, Phase 3 `ingest-adf`, Phase 4
`medallion`, Phase 7 `fabric-mirror`, Phase 10 `stream`, Phase 11
`validate-pbi`. The base install's `claims-azure --version` stays fast
even once `[azure]` + `[spark]` are installed.
"""

from __future__ import annotations

import argparse
import sys

from claims_azure import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claims-azure",
        description="Azure Databricks + Microsoft Fabric claims lakehouse CLI.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=False)
    subparsers.add_parser("version", help="Print the installed version and exit.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    _build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
