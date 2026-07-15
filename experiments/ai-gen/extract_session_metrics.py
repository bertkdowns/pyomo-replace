#!/usr/bin/env python3
"""Extract comparable metrics from OpenCode session exports.

The script reports facts stored in each ``session.json``. Solver success is
reported only when a model-run tool output contains an IPOPT success marker.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


MODEL_COMMAND = re.compile(r"\bpython(?:\d+(?:\.\d+)*)?\b.*\.py\b")
SUCCESS_MARKER = re.compile(r"optimal solution found|terminate(?:d)? optimally", re.I)

HEADERS = (
    "case",
    "model",
    "duration_s",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "patches",
    "lines_added",
    "lines_removed",
    "model_runs",
    "model_run_failures",
    "reported_optimal_runs",
)


def values(items: Iterable[dict[str, Any]], key: str) -> Iterable[dict[str, Any]]:
    """Yield mapping values whose type and key match the requested shape."""
    for item in items:
        value = item.get(key)
        if isinstance(value, dict):
            yield value


def patch_line_counts(patch: str) -> tuple[int, int]:
    """Return added and removed content lines from a unified diff."""
    added = removed = 0
    for line in patch.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def extract_metrics(session_path: Path, root: Path) -> dict[str, object]:
    with session_path.open(encoding="utf-8") as file:
        session = json.load(file)

    info = session["info"]
    tokens = info.get("tokens", {})
    cache = tokens.get("cache", {})
    time = info.get("time", {})
    created = time.get("created")
    updated = time.get("updated")
    duration_s = (updated - created) / 1000 if created is not None and updated is not None else None

    patches = lines_added = lines_removed = model_runs = model_run_failures = optimal_runs = 0
    for message in session.get("messages", []):
        for part in message.get("parts", []):
            if part.get("type") != "tool":
                continue
            state = part.get("state", {})
            if part.get("tool") == "apply_patch":
                patches += 1
                added, removed = patch_line_counts(state.get("input", {}).get("patchText", ""))
                lines_added += added
                lines_removed += removed
                continue
            if part.get("tool") != "bash":
                continue
            command = state.get("input", {}).get("command", "")
            if not MODEL_COMMAND.search(command):
                continue
            model_runs += 1
            metadata = state.get("metadata", {})
            if metadata.get("exit") not in (None, 0):
                model_run_failures += 1
            output = state.get("output", "")
            if SUCCESS_MARKER.search(output):
                optimal_runs += 1

    relative_case = session_path.parent.relative_to(root).as_posix()
    return {
        "case": relative_case,
        "model": info.get("model", {}).get("id"),
        "duration_s": duration_s,
        "input_tokens": tokens.get("input"),
        "output_tokens": tokens.get("output"),
        "reasoning_tokens": tokens.get("reasoning"),
        "cache_read_tokens": cache.get("read"),
        "cache_write_tokens": cache.get("write"),
        "patches": patches,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "model_runs": model_runs,
        "model_run_failures": model_run_failures,
        "reported_optimal_runs": optimal_runs,
    }


def write_markdown(rows: list[dict[str, object]]) -> None:
    print("| " + " | ".join(HEADERS) + " |")
    print("| " + " | ".join("---" for _ in HEADERS) + " |")
    for row in rows:
        print("| " + " | ".join(str(row[header] or "") for header in HEADERS) + " |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path(__file__).parent,
        help="Directory containing session.json files (default: this script's directory).",
    )
    parser.add_argument("--format", choices=("markdown", "csv"), default="markdown")
    args = parser.parse_args()

    root = args.directory.resolve()
    paths = sorted(root.rglob("session.json"))
    if not paths:
        parser.error(f"no session.json files found below {root}")
    rows = [extract_metrics(path, root) for path in paths]

    if args.format == "markdown":
        write_markdown(rows)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
