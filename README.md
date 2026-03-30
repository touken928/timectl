# timewarp

Command-line tool to inspect and adjust file and directory timestamps (`atime`, `mtime`, `btime`, and best-effort `ctime`).

> **Testing:** This project has **only been tested on macOS 26**. Behavior on other operating systems or versions is not guaranteed.

## Requirements

- Python 3.10 (see `pyproject.toml`)

## Install

**Recommended:** add the CLI from PyPI with uv’s tool installer (see [Using tools](https://docs.astral.sh/uv/guides/tools/)):

```bash
uv tool install timewarp
timewarp --help
```

To run a one-off command without installing the tool globally, use [`uvx`](https://docs.astral.sh/uv/guides/tools/) (alias for `uv tool run`):

```bash
uvx timewarp --help
uvx timewarp inspect .
```

You can also install from PyPI with pip:

```bash
pip install timewarp
timewarp --help
```

To work on this repository from a clone, use `uv sync` and `uv run timewarp …`.

## Commands

### `inspect`

Show `atime`, `mtime`, `ctime`, and `btime` (when available) for a single path. Times are printed in the system local timezone.

```bash
timewarp inspect              # default: current directory
timewarp inspect path/to/file
```

### `set`

Update timestamps for **one** root path (default: current directory). By default, **directories are processed recursively** (all entries under the tree).

```bash
timewarp set [path] [--time <value>] [--fields <letters>] [--no-recursive]
```

| Option | Description |
|--------|-------------|
| `--time` | Target time; default is `now`. See [Time formats](#time-formats). |
| `--fields` | Which fields to change: `a` (atime), `m` (mtime), `c` (ctime), `b` (btime). Default: `amcb`. |
| `--no-recursive` | Do not walk into subdirectories when `path` is a directory. |

**Field notes:**

- **`a` / `m`:** Set via `os.utime` to the value of `--time`.
- **`b`:** On macOS, the tool tries Apple’s `SetFile` (from Xcode Command Line Tools) when available; otherwise `b` may be skipped with a reason in the output.
- **`c`:** The system does not allow setting `ctime` to an arbitrary value. With `c` in `--fields`, the tool **refreshes `ctime` to the current moment** after other updates. Therefore **`c` is only allowed when `--time` is `now`** (including the default). If `--time` is anything else and `c` is included (including the default `amcb`), the command exits with an error—use e.g. `--fields amb` to omit `c`.

## Time formats

- `now`
- ISO 8601 (e.g. `2026-03-30T12:34:56+08:00`)
- `YYYY-MM-DD HH:MM:SS` (interpreted in the local timezone if no offset is given)
- Unix seconds: `@1711767296`
- Nanoseconds: `@1711767296000000000ns`

## Examples

```bash
# Inspect a file
timewarp inspect ./README.md

# Set everything to now under current directory (default path, --time, --fields)
timewarp set

# Set everything to now under a given root
timewarp set ./some/dir

# Set atime/mtime/btime to a fixed time (omit c)
timewarp set ./file.txt --time "2026-03-30 22:00:00" --fields amb

# Only touch the directory itself, not children
timewarp set ./folder --no-recursive --time now
```

## Limitations

- **`ctime`** cannot be set to a specific historical time; only a “touch to now” style refresh is supported, and only when `--time` is `now`.
- **`btime`** support depends on the platform and tools (on macOS, `SetFile` is used when present).
- Cross-platform and cross-filesystem timestamp semantics differ; this tool does not promise identical results outside the tested environment.

## License

This project is licensed under the [MIT License](LICENSE).
