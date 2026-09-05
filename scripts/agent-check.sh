#!/usr/bin/env bash
# pair-watchの検証。共有pre-push（hooks.runAgentCheck=true）から呼ばれる。
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/validate-package.py
if command -v claude >/dev/null 2>&1; then
  claude plugin validate .
fi
python3 -m unittest discover -s tests
bash scripts/check-protocol.sh
bash scripts/test-wait-for-message.sh
if command -v textlint >/dev/null 2>&1; then
  textlint --no-color --config .textlintrc.json README.ja.md
fi
