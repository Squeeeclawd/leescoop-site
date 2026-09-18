#!/usr/bin/env bash
# Compatibility entrypoint: deterministic plan only; no agent, images or publication.
# Uses only bash + python; no rg/ripgrep dependency in error paths.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/publishing_workflow.py" "$@" plan
