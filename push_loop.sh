#!/bin/bash
# Optional local alternative to the GitHub Action: fetch official results every
# 10 minutes and push only when the numbers actually change.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
echo "[push_loop] Starting results push loop in $REPO ..."

while true; do
  TIMESTAMP=$(date "+%Y-%m-%dT%H:%M:%S")
  git pull --rebase --quiet 2>/dev/null || true

  python3 fetch_election_results.py || echo "[$TIMESTAMP] fetch failed; will retry"

  if git diff --quiet results.json national_results.json 2>/dev/null; then
    echo "[$TIMESTAMP] No changes to commit."
  else
    git add results.json national_results.json
    git commit -m "Update official results: $TIMESTAMP"
    git push
    echo "[$TIMESTAMP] Pushed new results."
  fi
  sleep 600
done
