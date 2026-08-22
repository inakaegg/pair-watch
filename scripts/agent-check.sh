#!/usr/bin/env bash
# pair-watchの検証。共有pre-push（hooks.runAgentCheck=true）から呼ばれる。
set -euo pipefail
cd "$(dirname "$0")/.."
claude plugin validate .
if command -v textlint >/dev/null 2>&1; then
  textlint --no-color --config .textlintrc.json README.ja.md
fi
