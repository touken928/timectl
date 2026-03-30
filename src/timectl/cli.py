from __future__ import annotations

import argparse

from .inspect import add_inspect_parser, run_inspect
from .settime import add_set_parser, run_set


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="timectl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_inspect_parser(subparsers)
    add_set_parser(subparsers)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "inspect":
        raise SystemExit(run_inspect(args))
    if args.command == "set":
        raise SystemExit(run_set(args))
