#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier
python3 "$SCRIPT_DIR/verifier.py" "$SCRIPT_DIR/expected.json" /app/actions.jsonl /logs/verifier/report.json /logs/verifier/reward.txt
