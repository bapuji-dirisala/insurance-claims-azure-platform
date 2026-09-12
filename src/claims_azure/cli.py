"""claims-azure CLI entry point.

Subcommands are attached with **lazy imports** so a reader on a bare
install never pays the pandas / pyarrow / pyspark / azure-sdk cost just
to run ``claims-azure --version``. Each handler imports its own module
only when the user actually invokes it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from claims_azure import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claims-azure",
        description="Azure Databricks + Microsoft Fabric claims lakehouse CLI.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=False)
    subparsers.add_parser("version", help="Print the installed version and exit.")

    # Phase 2 — synthetic P&C generator.
    gen = subparsers.add_parser(
        "generate",
        help="Emit synthetic P&C datasets (parties, policies, endorsements, claims, payments, premiums).",
    )
    gen.add_argument(
        "dataset",
        choices=(
            "all",
            "parties",
            "policies",
            "endorsements",
            "claims",
            "payments",
            "premiums",
        ),
        help="Which dataset(s) to materialize.",
    )
    gen.add_argument(
        "--out",
        type=Path,
        default=Path("data/bronze/local"),
        help="Output directory (default: data/bronze/local).",
    )
    gen.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    gen.add_argument("--parties", type=int, default=2_000, help="Party count.")
    gen.add_argument("--policies", type=int, default=2_500, help="Policy count.")
    gen.add_argument("--endorsements", type=int, default=500, help="Endorsement count.")
    gen.add_argument("--claims", type=int, default=1_000, help="Claim count.")
    gen.add_argument("--payments", type=int, default=2_500, help="Payment count.")

    # Phase 3 — local ADF emulator.
    ing = subparsers.add_parser(
        "ingest-local",
        help="Run an ADF pipeline locally against Azurite (same bronze layout).",
    )
    ing.add_argument(
        "pipeline",
        choices=("claims-sftp", "policies-azsql"),
        help="Which ADF pipeline to emulate locally.",
    )
    ing.add_argument(
        "--out",
        type=Path,
        default=Path("__blobstorage__"),
        help="Local root directory (default: ./__blobstorage__ — Azurite's default location).",
    )
    ing.add_argument("--seed", type=int, default=42)

    return parser


def _handle_ingest_local(args: argparse.Namespace) -> int:
    from claims_azure.ingest.pipelines import (
        run_claims_sftp_to_bronze,
        run_policies_azsql_to_bronze,
    )

    if args.pipeline == "claims-sftp":
        path = run_claims_sftp_to_bronze(seed=args.seed, local_root=args.out)
    else:
        path = run_policies_azsql_to_bronze(seed=args.seed, local_root=args.out)
    print(f"  wrote → {path}")
    return 0


def _handle_generate(args: argparse.Namespace) -> int:
    """Lazy-import the generator so the base install stays fast."""
    from claims_azure.generator import GeneratorConfig, generate_bundle
    from claims_azure.generator.pipeline import write_bundle

    cfg = GeneratorConfig(
        seed=args.seed,
        num_parties=args.parties,
        num_policies=args.policies,
        num_endorsements=args.endorsements,
        num_claims=args.claims,
        num_payments=args.payments,
    )
    bundle = generate_bundle(cfg)
    written = write_bundle(bundle, args.out)
    for name, path in written.items():
        print(f"  {name:14s} → {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "generate":
        return _handle_generate(args)
    if args.command == "ingest-local":
        return _handle_ingest_local(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
