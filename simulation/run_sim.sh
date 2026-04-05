#!/usr/bin/env bash
# Backfill synthetic PlayPLTX events from N days ago through today.
# Run from repo root or from this directory: ./simulation/run_sim.sh 7
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAYS="${1:-1}"
if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [[ "$DAYS" -lt 1 ]]; then
  echo "Usage: $0 <days_back_positive_integer>" >&2
  exit 1
fi
exec python3 "$SCRIPT_DIR/generator.py" --days-back "$DAYS"
