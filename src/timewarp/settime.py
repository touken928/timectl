from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .timefmt import LOCAL_TIMEZONE, format_ns, parse_time_to_ns


def add_set_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    set_parser = subparsers.add_parser("set", help="Update times for one path recursively by default")
    set_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target path, defaults to current directory",
    )
    set_parser.add_argument(
        "--time",
        default="now",
        help='Target time, supports "now", ISO8601, "YYYY-MM-DD HH:MM:SS", and @unix timestamp (default: now)',
    )
    set_parser.add_argument(
        "--fields",
        default="amcb",
        help='Fields to update, combination of "a", "m", "c", "b" (default: amcb)',
    )
    set_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive traversal when target is a directory",
    )


def run_set(args: argparse.Namespace) -> int:
    try:
        fields = _parse_fields(args.fields)
    except ValueError as exc:
        print(f"error: invalid --fields value: {args.fields} ({exc})", file=sys.stderr)
        return 2

    if "c" in fields and args.time != "now":
        print('error: field "c" only supports time value "now"', file=sys.stderr)
        return 2

    try:
        target_ns = parse_time_to_ns(args.time)
    except ValueError as exc:
        print(f"error: invalid time value: {args.time} ({exc})", file=sys.stderr)
        return 2

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2

    targets = list(_iter_targets(root, recursive=not args.no_recursive))

    updated = 0
    failed = 0
    btime_updated = 0
    btime_skipped = 0
    ctime_touched = 0
    ctime_skipped = 0
    for path in targets:
        try:
            if "a" in fields or "m" in fields:
                stat_result = path.stat()
                atime_ns = target_ns if "a" in fields else stat_result.st_atime_ns
                mtime_ns = target_ns if "m" in fields else stat_result.st_mtime_ns
                os.utime(path, ns=(atime_ns, mtime_ns))
            updated += 1
            btime_text = "not-requested"
            if "b" in fields:
                btime_changed, btime_reason = _try_set_btime(path, target_ns)
                if btime_changed:
                    btime_updated += 1
                    btime_text = "updated"
                else:
                    btime_skipped += 1
                    btime_text = btime_reason

            ctime_text = "not-requested"
            if "c" in fields:
                ctime_changed, ctime_reason = _touch_ctime_now(path)
                if ctime_changed:
                    ctime_touched += 1
                    ctime_text = "touched-now"
                else:
                    ctime_skipped += 1
                    ctime_text = ctime_reason

            print(f"updated: {path} (btime: {btime_text}, ctime: {ctime_text})")
        except OSError as exc:
            print(f"warning: failed to update {path}: {exc}", file=sys.stderr)
            failed += 1

    target_display = format_ns(target_ns)["iso_local"]
    print(
        "done: "
        f"updated={updated}, failed={failed}, fields={''.join(sorted(fields))}, btime_updated={btime_updated}, "
        f"btime_skipped={btime_skipped}, ctime_touched={ctime_touched}, "
        f"ctime_skipped={ctime_skipped}, target={target_display}"
    )
    return 0 if failed == 0 else 1


def _iter_targets(root: Path, recursive: bool) -> Iterable[Path]:
    yield root
    if not recursive or not root.is_dir():
        return
    for child in root.rglob("*"):
        yield child


def _parse_fields(raw: str) -> set[str]:
    allowed = {"a", "m", "c", "b"}
    result = set(raw.strip().lower())
    if not result:
        raise ValueError("empty value")
    invalid = result - allowed
    if invalid:
        joined = "".join(sorted(invalid))
        raise ValueError(f"unsupported field(s): {joined}")
    return result


def _try_set_btime(path: Path, target_ns: int) -> tuple[bool, str]:
    if sys.platform != "darwin":
        return False, "unsupported-platform"

    setfile_bin = shutil.which("SetFile")
    if setfile_bin is None:
        return False, "SetFile-not-found"

    before_btime_ns = _read_btime_ns(path)
    target_dt = datetime.fromtimestamp(target_ns / 1_000_000_000, tz=LOCAL_TIMEZONE)
    # SetFile expects local wall-clock time like 03/30/2026 22:30:00.
    setfile_time = target_dt.strftime("%m/%d/%Y %H:%M:%S")
    result = subprocess.run(
        [setfile_bin, "-d", setfile_time, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        after_btime_ns = _read_btime_ns(path)
        if after_btime_ns is None:
            return False, "unable-to-read-btime"
        if abs(after_btime_ns - target_ns) <= 1_000_000_000:
            return True, "updated"
        if before_btime_ns is not None and after_btime_ns == before_btime_ns:
            return False, "no-observed-change"
        return False, "mismatch-after-update"
    reason = result.stderr.strip() or result.stdout.strip() or f"exit-{result.returncode}"
    return False, reason


def _read_btime_ns(path: Path) -> int | None:
    stat_result = path.stat()
    btime_ns = getattr(stat_result, "st_birthtime_ns", None)
    if btime_ns is not None:
        return btime_ns
    birthtime_seconds = getattr(stat_result, "st_birthtime", None)
    if birthtime_seconds is not None:
        return int(birthtime_seconds * 1_000_000_000)
    return None


def _touch_ctime_now(path: Path) -> tuple[bool, str]:
    before = path.stat().st_ctime_ns
    stat_result = path.stat()
    try:
        # ctime cannot be set directly; re-applying timestamps asks kernel
        # to update inode metadata time to "now".
        os.utime(path, ns=(stat_result.st_atime_ns, stat_result.st_mtime_ns))
    except OSError as exc:
        return False, str(exc)
    after = path.stat().st_ctime_ns
    if after > before:
        return True, "touched-now"
    return False, "no-observed-change"
