from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .timefmt import format_ns


@dataclass
class InspectRecord:
    path: str
    kind: str
    atime_ns: int
    mtime_ns: int
    ctime_ns: int
    btime_ns: int | None


def add_inspect_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    inspect_parser = subparsers.add_parser("inspect", help="Show file and directory times")
    inspect_parser.add_argument("path", nargs="?", default=".", help="Target path, defaults to current directory")


def run_inspect(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    records: list[InspectRecord] = []
    if not path.exists():
        print(f"warning: path not found: {path}", file=sys.stderr)
    else:
        try:
            records.append(_read_record(path))
        except OSError as exc:
            print(f"warning: failed to inspect {path}: {exc}", file=sys.stderr)
    print(_render_text(records))
    return 0


def _detect_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "dir"
    if path.is_file():
        return "file"
    return "other"


def _read_record(path: Path) -> InspectRecord:
    stat_result = path.stat()
    btime_ns = getattr(stat_result, "st_birthtime_ns", None)
    if btime_ns is None:
        birthtime_seconds = getattr(stat_result, "st_birthtime", None)
        if birthtime_seconds is not None:
            btime_ns = int(birthtime_seconds * 1_000_000_000)
    return InspectRecord(
        path=str(path),
        kind=_detect_kind(path),
        atime_ns=stat_result.st_atime_ns,
        mtime_ns=stat_result.st_mtime_ns,
        ctime_ns=stat_result.st_ctime_ns,
        btime_ns=btime_ns,
    )


def _render_text(records: list[InspectRecord]) -> str:
    lines: list[str] = []
    for record in records:
        lines.append(f"{record.path} [{record.kind}]")
        lines.append(f"  atime: {format_ns(record.atime_ns)['iso_local']}")
        lines.append(f"  mtime: {format_ns(record.mtime_ns)['iso_local']}")
        lines.append(f"  ctime: {format_ns(record.ctime_ns)['iso_local']}")
        btime_text = format_ns(record.btime_ns)["iso_local"] if record.btime_ns is not None else "unsupported"
        lines.append(f"  btime: {btime_text}")
    return "\n".join(lines)
