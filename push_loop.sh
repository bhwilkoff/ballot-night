#!/bin/bash
# Election night push loop - runs every 10 minutes, writes data and pushes to GitHub
set -e

REPO="/Users/bhwilkoff/.gemini/antigravity/scratch/ballot-night"
FETCHER="$REPO/fetch_election_results.py"

echo "[push_loop] Starting election night push loop..."

while true; do
  NOW=$(date "+%H:%M")
  TIMESTAMP=$(date "+%Y-%m-%dT%H:%M:%S MT")
  echo "[$TIMESTAMP] Running fetcher..."

  cd "$REPO"
  git pull --rebase --quiet 2>/dev/null || true

  python3 "$FETCHER" --stage live

  # Check if anything changed
  if git diff --quiet results.json national_results.json 2>/dev/null; then
    echo "[$TIMESTAMP] No changes to commit."
  else
    git add results.json national_results.json
    git commit -m "Auto-update: $TIMESTAMP"
    git push
    echo "[$TIMESTAMP] Pushed new results."
  fi

  echo "[$TIMESTAMP] Sleeping 10 minutes..."
  sleep 600
done
