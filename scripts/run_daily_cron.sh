#!/usr/bin/env bash
# Compatibility entrypoint: deterministic plan only; no agent, images or publication.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/publishing_workflow.py" "$@" plan
