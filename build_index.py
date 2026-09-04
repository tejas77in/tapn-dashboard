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
content) is taken verbatim from dashboard.html, so any future layout
change there flows through automatically.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE.parent / "dashboard.html" if (HERE.parent / "dashboard.html").exists() else HERE / "dashboard.html"
DST = HERE / "index.html"

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


def main():
    if not SRC.exists():
        print(f"ERROR: source {SRC} not found", file=sys.stderr)
        sys.exit(1)
    src = SRC.read_text()

    gate_hash = "REPLACE_VIA_set_password.sh"
    if DST.exists():
        m = re.search(r'const GATE_HASH = "([0-9a-f]+)";', DST.read_text())
        if m:
            gate_hash = m.group(1)
        else:
            print("WARNING: could not find existing GATE_HASH in index.html -- "
                  "keeping placeholder, run set_password.sh after this.", file=sys.stderr)

    out = src.replace(
        '<meta http-equiv="refresh" content="60">',
        '<meta name="robots" content="noindex,nofollow">',
        1,
    )

    out = out.replace("</style>", GATE_CSS + "</style>", 1)

    out = re.sub(r'(<body[^>]*>)', r'\1' + GATE_OVERLAY_HTML, out, count=1)
    gate_script = GATE_SCRIPT_TMPL.format(gate_hash=gate_hash)
    idx = out.rfind("</body>")
    if idx == -1:
        print("ERROR: no </body> found in dashboard.html", file=sys.stderr)
        sys.exit(1)
    out = out[:idx] + gate_script.lstrip("\n") + out[idx + len("</body>"):]

    DST.write_text(out)
    print(f"Rebuilt {DST} from {SRC} (gate_hash={'preserved' if gate_hash != 'REPLACE_VIA_set_password.sh' else 'MISSING'})")


if __name__ == "__main__":
    main()
