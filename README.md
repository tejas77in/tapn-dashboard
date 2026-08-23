# TAPN Dashboard -- published (read-only) copy

This is a **read-only snapshot** of the TAPN trading dashboard, meant to be
published to Vercel so you can check it from your phone/browser on your
own domain. It does NOT run any trading logic and holds no Tastytrade/UW
credentials -- bot.py keeps running locally on your Mac exactly as
before; this repo just publishes a copy of its output (`dashboard_data.js`).

Refresh model chosen: **manual**. The published page only updates when
you run `./publish.sh`. It will not silently go stale-looking -- the page
still shows the ⚠ stale banner if `updated` is more than 15 minutes old,
same as the local dashboard.

## One-time setup

1. **Set your password** (never leaves your machine as plaintext):
   ```
   ./set_password.sh
   ```
   Copy the printed hash into `index.html`, replacing
   `REPLACE_WITH_YOUR_HASH` on the `const GATE_HASH = ...` line.

2. **Create a GitHub repo** (e.g. `tapn-dashboard`) and push this folder:
   ```
   git init
   git add .
   git commit -m "Initial dashboard publish"
   git branch -M main
   git remote add origin https://github.com/<you>/tapn-dashboard.git
   git push -u origin main
   ```

3. **Import into Vercel**: Vercel dashboard -> Add New -> Project ->
   Import the `tapn-dashboard` repo. Framework preset: "Other" (it's
   plain static HTML, no build step needed). Deploy.

4. **Point your domain at it**: in the Vercel project -> Settings ->
   Domains -> add your domain (or a subdomain like
   `dashboard.yourdomain.com`) and follow Vercel's DNS instructions.

## Updating the published data

Whenever you want the published page to reflect current numbers:
```
./publish.sh
```
This copies the latest `dashboard_data.js` from your local TAPN folder,
commits, and pushes -- Vercel auto-redeploys on push (usually live within
30-60 seconds). `index.html` is untouched by this script, so your
`GATE_HASH` edit persists across every publish.

## Security notes

- The password gate is **client-side only** -- it stops casual/accidental
  discovery of the link, not a determined attacker who inspects the page
  source (the gated content is present in the HTML, just visually
  hidden until unlock). If you want real access control, Vercel's
  built-in Deployment Protection (Pro plan) puts the password check at
  the edge, before any content is served.
- `robots.txt` and an `X-Robots-Tag` header (via `vercel.json`) ask
  search engines not to index the page. This isn't a security boundary
  either, just reduces accidental discoverability.
- No trading credentials, API keys, or order-placement code exist
  anywhere in this repo. It is purely a static viewer for
  `dashboard_data.js`.
