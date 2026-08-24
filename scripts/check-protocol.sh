#!/usr/bin/env bash
set -euo pipefail

# This checker intentionally pins literal wording in the protocol documents.
# When prose changes, update the document and its assertion together; do not weaken
# or delete an assertion merely to make a documentation edit pass.

cd "$(dirname "$0")/.."

fail() {
  printf 'protocol check failed: %s\n' "$1" >&2
  exit 1
}

require_literal() {
  local file=$1
  local text=$2
  grep -Fq -- "$text" "$file" || fail "$file is missing: $text"
}

reject_literal() {
  local file=$1
  local text=$2
  if grep -Fq -- "$text" "$file"; then
    fail "$file still contains: $text"
  fi
}

skill=plugins/pair-watch/skills/pair-watch/SKILL.md
transport=plugins/pair-watch/skills/pair-watch/references/transport-codex.md
brief=plugins/pair-watch/skills/pair-watch/assets/impl-brief-codex.md
prompts=plugins/pair-watch/skills/pair-watch/assets/user-prompts.md
agent=plugins/pair-watch/skills/pair-watch/agents/openai.yaml
watch_script=plugins/pair-watch/skills/pair-watch/scripts/wait-for-message.sh

test -x "$watch_script" || fail "$watch_script is missing or not executable"

require_literal "$skill" 'Codex + Codex'
require_literal "$skill" 'PAIR_MSG_END seq=<N>'
require_literal "$skill" 'fresh-context Codex'
require_literal "$skill" '{WATCH_SCRIPT}'
reject_literal "$skill" 'Codex can only be the implementer'

require_literal "$transport" 'Codex watcher + Codex implementer'
require_literal "$transport" 'one unacknowledged message'
require_literal "$transport" 'process every completed unprocessed message in sequence order'
require_literal "$transport" 'WATCH_ENDED role=watcher'
require_literal "$transport" 'exclude the watcher'

require_literal "$brief" '{WATCH_SCRIPT}'
require_literal "$brief" 'PAIR_MSG_END seq=<N>'
require_literal "$brief" 'WATCH_ENDED role=implementer'
require_literal "$brief" 'start declaration or any other outbox message that needs a watcher reply'

require_literal "$prompts" 'codex-watcher-nudge'
require_literal "$agent" 'Codex watcher'

require_literal README.md 'Codex + Codex'
require_literal README.ja.md 'Codex + Codex'

printf 'PASS: pair-watch protocol invariants\n'
