#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/shmee/Desktop/leescoop"
PROMPT="$ROOT/prompts/leescoop_daily_cron_command.md"
LOG_DIR="$ROOT/tmp/cron-logs"
mkdir -p "$LOG_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
SESSION_KEY="agent:main:leescoop-daily-autopost:$STAMP"
OUT="$(mktemp)"
ERR="$LOG_DIR/leescoop-daily-cron-$STAMP.err.log"

cleanup() {
  rm -f "$OUT"
}
trap cleanup EXIT

if ! openclaw agent \
  --local \
  --model openai/gpt-5.4 \
  --session-key "$SESSION_KEY" \
  --message-file "$PROMPT" \
  --json \
  --timeout 7200 \
  >"$OUT" 2>"$ERR"; then
  echo "LeeScoop daily runner failed. stderr log: $ERR"
  cat "$ERR"
  if [[ -s "$OUT" ]]; then
    cat "$OUT"
  fi
  exit 1
fi

REPORT="$(jq -r '.payloads[0].text // empty' "$OUT")"
if [[ -z "$REPORT" ]]; then
  echo "LeeScoop daily runner produced no report text. stderr log: $ERR"
  cat "$ERR"
  cat "$OUT"
  exit 1
fi

printf '%s\n' "$REPORT"
