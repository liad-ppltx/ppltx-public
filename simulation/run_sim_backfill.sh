#!/usr/bin/env bash
# Backfill synthetic events for N days, then upload local JSONL to BigQuery (bq_config.json).
# Usage: ./run_sim_backfill.sh 7
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAYS="${1:-7}"
if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [[ "$DAYS" -lt 1 ]]; then
  echo "Usage: $0 <days_back_positive_integer>" >&2
  exit 1
fi
python3 "$SCRIPT_DIR/generator.py" --days-back "$DAYS"
python3 "$SCRIPT_DIR/generator.py" upload-bq --config "$SCRIPT_DIR/bq_config.json"
