#!/bin/bash
# Generates the SHA-256 hash for your dashboard gate password and prints
# it -- paste the printed hash into index.html, replacing
# REPLACE_WITH_YOUR_HASH. The plaintext password is never written to
# disk or committed to git; only this one-way hash goes into the repo.
set -e
read -s -p "Choose a password for the published dashboard: " PW
echo
HASH=$(printf '%s' "$PW" | shasum -a 256 | cut -d' ' -f1)
echo
echo "Hash: $HASH"
echo
echo "Now open index.html, find:"
echo '  const GATE_HASH = "REPLACE_WITH_YOUR_HASH";'
echo "and replace REPLACE_WITH_YOUR_HASH with the hash above."
