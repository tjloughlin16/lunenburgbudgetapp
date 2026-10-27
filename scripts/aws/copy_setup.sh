#!/usr/bin/env bash
# Put the Textract setup on the clipboard, wrapped so that pasting it into AWS CloudShell WRITES
# the script to a file instead of running it line by line. Then, in CloudShell:
#     bash setup_textract.sh you@example.com
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
{ printf "cat > setup_textract.sh <<'LUNENBURG_EOF'\n"; cat "$here/setup_textract.sh"; printf "LUNENBURG_EOF\n"
  printf "echo 'saved. now run:  bash setup_textract.sh YOUR_EMAIL'\n"; } | pbcopy
echo "on the clipboard: $(pbpaste | wc -l | tr -d ' ') lines. Paste into CloudShell."
