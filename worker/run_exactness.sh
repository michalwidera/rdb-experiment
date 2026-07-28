#!/usr/bin/env bash
# Zgodnosciowy punkt wejscia. Wlasciwy, samodzielny harness K18 znajduje sie
# razem z manifestem i README eksperymentu.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

exec "$EXPERIMENT_REPO/results_20260728_K18/run.sh" "$@"
