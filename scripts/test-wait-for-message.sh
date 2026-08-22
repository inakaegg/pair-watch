#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

watch_script=plugins/pair-watch/skills/pair-watch/scripts/wait-for-message.sh
test -x "$watch_script"

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/pair-watch-sequence.XXXXXX")
trap 'rm -rf "$tmp_dir"' EXIT
message_file=$tmp_dir/messages.md

assert_output() {
  local expected=$1
  shift
  local actual
  actual=$("$@")
  test "$actual" = "$expected"
}

printf '%s\n' 'first' 'PAIR_MSG_END seq=1' 'second' 'PAIR_MSG_END seq=2' > "$message_file"
assert_output 2 "$watch_script" "$message_file" 1 0 0

printf '%s\n' 'first' 'PAIR_MSG_END seq=1' > "$message_file"
(
  sleep 1
  printf '%s\n' 'second' 'PAIR_MSG_END seq=2' >> "$message_file"
) &
writer_pid=$!
assert_output 2 "$watch_script" "$message_file" 1 1 3
wait "$writer_pid"

printf '%s\n' 'first' 'PAIR_MSG_END seq=1' 'incomplete second' > "$message_file"
if "$watch_script" "$message_file" 1 0 0 >/dev/null; then
  printf 'incomplete message unexpectedly woke the watcher\n' >&2
  exit 1
fi

printf '%s\n' 'first' 'PAIR_MSG_END seq=1' > "$message_file"
if "$watch_script" "$message_file" 1 0 1 >/dev/null; then
  printf 'timeout unexpectedly reported a new message\n' >&2
  exit 1
fi

printf '%s\n' 'newest' 'PAIR_MSG_END seq=3' 'older' 'PAIR_MSG_END seq=2' > "$message_file"
assert_output 3 "$watch_script" "$message_file" 1 0 0

printf 'PASS: wait-for-message reply-before-watch, in-watch, incomplete, timeout, and burst cases\n'
