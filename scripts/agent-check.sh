#!/usr/bin/env bash
# pair-watchの検証。共有pre-push（hooks.runAgentCheck=true）から呼ばれる。
set -euo pipefail
# The shared pre-push hook exports GIT_DIR / GIT_WORK_TREE etc. for this repository. The tests
# create throwaway repositories and worktrees; with those variables inherited, git would act on
# this repository instead. Drop them here so the tests are isolated whoever runs them.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR GIT_PREFIX GIT_ALTERNATE_OBJECT_DIRECTORIES
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
