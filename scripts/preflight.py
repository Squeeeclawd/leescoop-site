#!/usr/bin/env python3
"""LeeScoop batch-run preflight.

Run before a LeeScoop batch to catch the dumb stuff first:
working tree surprises, stale candidate files, missing assets, and unavailable local gates.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"


def run(cmd: list[str], *, check: bool = False) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip())
    return proc.returncode, proc.stdout.strip()


def newest_candidate() -> Path | None:
    if not TMP.exists():
        return None
    candidates = sorted(TMP.glob("*candidate*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def summarize_candidate(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = data.get("events", []) if isinstance(data, dict) else []
        news = data.get("news", []) if isinstance(data, dict) else []
        return f"{len(events)} event(s), {len(news)} news item(s)"
    except Exception as exc:
        return f"unreadable JSON: {exc}"


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    print("LeeScoop preflight")
    print("==================")

    code, status = run(["git", "status", "--short"])
    if code != 0:
        failures.append("git status failed")
    elif status:
        warnings.append("working tree has uncommitted changes; confirm these are intentional before a batch run")

    code, branch = run(["git", "status", "--short", "--branch"])
    if branch:
        print(f"\nGit:\n{branch}")

    cand = newest_candidate()
    if cand:
        age_hours = (datetime.now(timezone.utc).timestamp() - cand.stat().st_mtime) / 3600
        print(f"\nNewest candidate file: {cand.relative_to(ROOT)} ({age_hours:.1f}h old, {summarize_candidate(cand)})")
        if age_hours > 24:
            warnings.append(f"newest candidate file is stale: {cand.relative_to(ROOT)}")
    else:
        warnings.append("no tmp/*candidate*.json file found")

    print("\nRunning content validation...")
    code, output = run([sys.executable, "scripts/validate_site.py"])
    print(output)
    if code != 0:
        failures.append("content validation failed")

    code, npm = run(["npm", "--version"])
    if code != 0:
        failures.append("npm is unavailable")
    else:
        print(f"\nnpm: {npm}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nPreflight complete. No hard blockers found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
