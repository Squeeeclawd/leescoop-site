#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/shmee/Desktop/leescoop"
PROMPT="$ROOT/prompts/leescoop_daily_cron_command.md"
LOG_DIR="$ROOT/tmp/cron-logs"
mkdir -p "$LOG_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
SESSION_KEY="agent:main:leescoop-daily-autopost:$STAMP"
MODEL="${LEESCOOP_DAILY_MODEL:-openai/gpt-5.5}"
OUT="$LOG_DIR/leescoop-daily-cron-$STAMP.json"
ERR="$LOG_DIR/leescoop-daily-cron-$STAMP.err.log"

extract_report() {
  jq -r '.payloads[0].text // empty' "$OUT" 2>/dev/null || true
}

if ! openclaw agent \
  --local \
  --model "$MODEL" \
  --session-key "$SESSION_KEY" \
  --message-file "$PROMPT" \
  --json \
  --timeout 7200 \
  >"$OUT" 2>"$ERR"; then
  REPORT="$(extract_report)"
  if [[ -n "$REPORT" ]] && rg -q "CLI transcript compaction failed.*Compaction timed out" "$ERR"; then
    echo "LeeScoop daily runner recovered from post-run compaction timeout. stderr log: $ERR; json log: $OUT" >&2
    printf '%s\n' "$REPORT"
    exit 0
  fi

  echo "LeeScoop daily runner failed. stderr log: $ERR"
  cat "$ERR"
  if [[ -s "$OUT" ]]; then
    echo "LeeScoop daily runner JSON log: $OUT"
    cat "$OUT"
  fi
  exit 1
fi

REPORT="$(extract_report)"
if [[ -z "$REPORT" ]]; then
  echo "LeeScoop daily runner produced no report text. stderr log: $ERR; json log: $OUT"
  cat "$ERR"
  cat "$OUT"
  exit 1
fi

printf '%s\n' "$REPORT"
