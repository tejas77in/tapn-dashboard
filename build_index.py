#!/usr/bin/env python3
"""
2026-09-04: auto-sync vercel-dashboard/index.html from the local
dashboard.html bot.py serves, so a layout edit to dashboard.html no
longer requires a manual copy/merge into index.html before it reaches
the published Vercel site. Run by publish.sh on every launchd cycle
(every 15 min) -- idempotent (no-ops into an unchanged file if
dashboard.html hasn't changed), and always re-applies the same three
Vercel-only additions on top of dashboard.html's current content:
  1. <meta name="robots" content="noindex,nofollow"> in place of
     dashboard.html's <meta http-equiv="refresh" content="60"> (the
     published copy doesn't need a hard auto-refresh meta -- it's
     already re-fetched by the dashboard's own JS poll).
  2. The client-side password gate (CSS + overlay HTML + unlock
     script), wrapping dashboard.html's <body> content in a
     #dash-content div that's hidden until the gate unlocks.
  3. GATE_HASH is preserved from whatever index.html currently has
     on disk (read back before rebuilding) -- this script never
     changes the password itself. set_password.sh remains the only
     way to change it.
Everything else (all of <head>'s <style>, and the entire <body>
content) is taken verbatim from each source page, so any future layout
change there flows through automatically.

2026-09-14: extended from a single dashboard.html -> index.html build
to a small list of PAGES (per explicit request, "moonshot paper trade
is getting big.. create a tab that lands to a different page for that
table and even IV edge and IV Crush") -- moonshot.html, iv_edge.html,
and ivcrush.html were split off the main dashboard into their own
static pages, linked via a shared nav bar (dashboard.html's own
docstring/comment has the design rationale). Each page keeps the SAME
published filename it has locally (moonshot.html -> moonshot.html,
etc.) EXCEPT the main page, which is still published as index.html for
root-URL convenience -- so the nav bar's "Dashboard" tab (which points
at "dashboard.html" in every page's local copy, since that's the real
local filename) gets that one href rewritten to "index.html" on every
published page, main or sub, so the tab keeps working after publish.
All four published pages get the SAME password gate (same GATE_HASH,
read from the existing index.html) -- sessionStorage's 'tapn_gate_ok'
flag is shared across same-origin pages in one browser tab, so
unlocking once on any page unlocks all four for that session.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
TAPN_ROOT = HERE.parent if (HERE.parent / "dashboard.html").exists() else HERE

# (source filename in the TAPN root, published filename in vercel-dashboard)
PAGES = [
    ("dashboard.html", "index.html"),
    ("spx_live.html", "spx_live.html"),  # 2026-09-19: SPX Live tab
    ("moonshot.html", "moonshot.html"),
    # 2026-09-19: iv_edge.html removed -- IV Edge deleted (thin/inconclusive, retired).
    # 2026-09-19: ivcrush.html removed -- IV Crush deleted (10.5% win rate,
    # negative signal). mrstonk.html will be added here once built.
    ("smart_money.html", "smart_money.html"),  # 2026-09-14: Smart Money tab
    ("spx_multistrat.html", "spx_multistrat.html"),  # 2026-09-15: SPX Multi-Structure tab
    ("leap_conviction.html", "leap_conviction.html"),  # 2026-09-15: LEAP Conviction tab
]

GATE_CSS = """  /* --- password gate (added for the published Vercel copy only -- not
     present on the local dashboard.html bot.py serves. Client-side only,
     meant to stop casual/accidental discovery of the link, not a real
     security boundary. GATE_HASH below is a SHA-256 hex digest set via
     set_password.sh -- see README.md -- the plaintext password is never
     stored in this file or committed to git. --- */
  #gate-overlay { position:fixed; inset:0; background:var(--bg); display:flex;
    align-items:center; justify-content:center; z-index:9999; }
  #gate-box { text-align:center; }
  #gate-pw { padding:8px 12px; border-radius:6px; border:1px solid var(--border);
    background:var(--card); color:var(--text); font-size:14px; }
  #gate-btn { padding:8px 14px; border-radius:6px; border:none; background:var(--blue);
    color:var(--bg); font-weight:600; cursor:pointer; margin-left:6px; }
  #gate-err { color:var(--red); margin-top:8px; font-size:12px; height:14px; }
"""

GATE_OVERLAY_HTML = """
<div id="gate-overlay">
  <div id="gate-box">
    <div style="margin-bottom:12px;font-size:16px;">TAPN Trading Technologies</div>
    <input id="gate-pw" type="password" placeholder="Password" autofocus>
    <button id="gate-btn">Unlock</button>
    <div id="gate-err"></div>
  </div>
</div>

<div id="dash-content" style="display:none">
"""

GATE_SCRIPT_TMPL = """
</div><!-- #dash-content -->

<script>
// --- password gate logic ---
// GATE_HASH is a SHA-256 hex digest of your chosen password, generated
// locally via set_password.sh -- see README.md. Never commit the
// plaintext password anywhere, only this hash.
const GATE_HASH = "{gate_hash}";

async function sha256Hex(str) {{
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}}
function revealDashboard() {{
  document.getElementById('gate-overlay').style.display = 'none';
  document.getElementById('dash-content').style.display = '';
}}
async function tryUnlock() {{
  const pw = document.getElementById('gate-pw').value;
  const hash = await sha256Hex(pw);
  if (hash === GATE_HASH) {{
    sessionStorage.setItem('tapn_gate_ok', '1');
    revealDashboard();
  }} else {{
    document.getElementById('gate-err').textContent = 'Incorrect password';
  }}
}}
document.getElementById('gate-btn').addEventListener('click', tryUnlock);
document.getElementById('gate-pw').addEventListener('keydown', e => {{ if (e.key === 'Enter') tryUnlock(); }});
if (sessionStorage.getItem('tapn_gate_ok') === '1') revealDashboard();
</script>

</body>
"""


def read_gate_hash(index_path: Path) -> str:
    gate_hash = "REPLACE_VIA_set_password.sh"
    if index_path.exists():
        m = re.search(r'const GATE_HASH = "([0-9a-f]+)";', index_path.read_text())
        if m:
            gate_hash = m.group(1)
        else:
            print("WARNING: could not find existing GATE_HASH in index.html -- "
                  "keeping placeholder, run set_password.sh after this.", file=sys.stderr)
    return gate_hash


def build_one(src_name: str, dst_name: str, gate_hash: str):
    src = TAPN_ROOT / src_name
    dst = HERE / dst_name
    if not src.exists():
        print(f"WARNING: source {src} not found, skipping {dst_name}", file=sys.stderr)
        return
    out = src.read_text()

    out = out.replace(
        '<meta http-equiv="refresh" content="60">',
        '<meta name="robots" content="noindex,nofollow">',
        1,
    )

    # 2026-09-14: every page's nav bar links to "dashboard.html" locally
    # (its real local filename) -- rewrite that ONE href to "index.html"
    # so the tab still resolves once published, since the main page is
    # published as index.html, not dashboard.html.
    out = out.replace('href="dashboard.html"', 'href="index.html"')

    out = out.replace("</style>", GATE_CSS + "</style>", 1)

    out = re.sub(r'(<body[^>]*>)', r'\1' + GATE_OVERLAY_HTML, out, count=1)
    gate_script = GATE_SCRIPT_TMPL.format(gate_hash=gate_hash)
    idx = out.rfind("</body>")
    if idx == -1:
        print(f"ERROR: no </body> found in {src_name}", file=sys.stderr)
        return
    out = out[:idx] + gate_script.lstrip("\n") + out[idx + len("</body>"):]

    dst.write_text(out)
    print(f"Rebuilt {dst} from {src}")


def main():
    index_path = HERE / "index.html"
    gate_hash = read_gate_hash(index_path)
    for src_name, dst_name in PAGES:
        build_one(src_name, dst_name, gate_hash)
    print(f"gate_hash={'preserved' if gate_hash != 'REPLACE_VIA_set_password.sh' else 'MISSING'}")


if __name__ == "__main__":
    main()
