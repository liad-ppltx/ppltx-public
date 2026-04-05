#!/usr/bin/env bash
# Daily job: simulate today (1 day window) and append to BigQuery. Intended for crontab.
# Example crontab (02:15 UTC): 15 2 * * * /path/to/ppltx-public/simulation/run_sim_daily.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/generator.py" --days-back 1
python3 "$SCRIPT_DIR/generator.py" upload-bq --config "$SCRIPT_DIR/bq_config.json"
