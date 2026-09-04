#!/bin/bash
# Runs on launchd's 15-min schedule (com.tejas.tapn-dashboard-publish.plist)
# and copies the latest dashboard_data.js AND rebuilds index.html from the
# live TAPN bot folder's dashboard.html, then pushes both to GitHub, which
# triggers a Vercel redeploy automatically. 2026-09-04: index.html IS now
# rebuilt every run (via build_index.py) so a layout edit to dashboard.html
# reaches the published site automatically -- GATE_HASH is preserved
# across rebuilds (read back from the existing index.html each time), so
# it's still safe; only set_password.sh changes it.
set -e
cd "$(dirname "$0")"

# 2026-08-19: mirror all output (including the exact git push error, if
# any) into a log INSIDE this repo -- separate from whatever
# StandardOutPath/StandardErrorPath the launchd plist points at, since
# those live outside TAPN and aren't always reachable for debugging. This
# is the file to check first if a publish attempt silently doesn't show
# up on the live site.
exec >> "$(dirname "$0")/publish_debug.log" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') (PATH=$PATH) ==="

# 2026-08-19: fixed stale path -- this used to point at
# "/Volumes/WD_Extention/Claude Automation bot/TAPN" (a folder that no
# longer exists; TAPN lives directly under WD_Extention), so the cp below
# always failed and `set -e` killed the script before it ever reached the
# git add/commit/push, which is why the published dashboard never updated
# even though bot.py's own dashboard_data.js was refreshing fine.
TAPN_DIR="/Volumes/WD_Extention/TAPN"
cp "$TAPN_DIR/dashboard_data.js" ./dashboard_data.js

# 2026-09-04 (per explicit request, "make sure when we change dashboard.html
# it automatically updates the github repo and vercel website"): rebuild
# index.html from the current dashboard.html on every cycle before
# deciding what to commit. build_index.py re-applies the Vercel-only
# additions (noindex meta, password gate) on top of whatever dashboard.html
# currently says, preserving the existing GATE_HASH -- so a layout edit
# made directly to dashboard.html now reaches the published site within
# one 15-min publish cycle with no manual copy/merge step, same as
# dashboard_data.js already did. Idempotent: no diff if dashboard.html
# hasn't changed since the last run.
python3 build_index.py

git add dashboard_data.js index.html
if git diff --cached --quiet; then
  echo "No changes since last publish -- nothing to push."
  exit 0
fi
git commit -m "Update dashboard $(date '+%Y-%m-%d %H:%M %Z')"

# 2026-08-19: sync with the remote before pushing -- every push was being
# rejected as non-fast-forward (remote had commits this local clone never
# pulled, likely from direct GitHub/Vercel interaction while this script
# was broken by the stale-path bug above). -X ours auto-resolves any
# conflicting hunk in our favor (we always want the freshly-copied
# dashboard_data.js to win, since that's the whole point of this script),
# while still cleanly picking up any other real remote changes (e.g. an
# index.html edit made directly on GitHub) instead of clobbering them.
git pull --no-edit -X ours origin main
git push

echo "Pushed. Vercel will redeploy automatically (usually live within ~30-60s)."
