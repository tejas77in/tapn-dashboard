#!/bin/bash
# Manual refresh: copies the latest dashboard_data.js from the live TAPN
# bot folder into this repo and pushes to GitHub, which triggers a Vercel
# redeploy automatically. Run this any time you want the published
# dashboard to reflect current data. index.html is NOT overwritten by
# this script (it only changes when you edit the dashboard layout
# yourself), so your GATE_HASH edit is safe to keep across runs.
set -e
cd "$(dirname "$0")"

TAPN_DIR="/Volumes/WD_Extention/Claude Automation bot/TAPN"
cp "$TAPN_DIR/dashboard_data.js" ./dashboard_data.js

git add dashboard_data.js
if git diff --cached --quiet; then
  echo "No changes since last publish -- nothing to push."
  exit 0
fi
git commit -m "Update dashboard data $(date '+%Y-%m-%d %H:%M %Z')"
git push

echo "Pushed. Vercel will redeploy automatically (usually live within ~30-60s)."
