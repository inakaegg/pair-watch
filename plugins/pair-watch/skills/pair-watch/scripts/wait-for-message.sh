#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'usage: %s FILE LAST_SEEN_SEQUENCE [POLL_SECONDS] [MAX_POLLS]\n' "$0" >&2
  exit 2
}

is_uint() {
  case $1 in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

test "$#" -ge 2 && test "$#" -le 4 || usage

message_file=$1
last_seen=$2
poll_seconds=${3:-5}
max_polls=${4:-58}

test -f "$message_file" || {
  printf 'message file not found: %s\n' "$message_file" >&2
  exit 2
}
is_uint "$last_seen" || usage
is_uint "$poll_seconds" || usage
is_uint "$max_polls" || usage

latest_complete_sequence() {
  awk '
    NF == 2 && $1 == "PAIR_MSG_END" && $2 ~ /^seq=[0-9]+$/ {
      sequence = $2
      sub(/^seq=/, "", sequence)
      sequence += 0
      if (sequence > latest) {
        latest = sequence
      }
    }
    END { print latest + 0 }
  ' "$message_file"
}

polls=0
while :; do
  if ! latest=$(latest_complete_sequence 2>/dev/null); then
    latest=$last_seen
  fi
  if test "$latest" -gt "$last_seen"; then
    printf '%s\n' "$latest"
    exit 0
  fi

  test "$polls" -lt "$max_polls" || exit 1
  sleep "$poll_seconds"
  polls=$((polls + 1))
done
