#!/usr/bin/env bash
# pair-watchの検証。共有pre-push（hooks.runAgentCheck=true）から呼ばれる。
set -euo pipefail
cd "$(dirname "$0")/.."
claude plugin validate .
bash scripts/check-protocol.sh
bash scripts/test-wait-for-message.sh
if command -v textlint >/dev/null 2>&1; then
  textlint --no-color --config .textlintrc.json README.ja.md
fi
