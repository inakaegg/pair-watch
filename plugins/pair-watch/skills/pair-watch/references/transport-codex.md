# Transport for a Codex peer — sequenced files + rollout audit

When the implementer seat is an interactive Codex CLI chat, this replaces **only the launch,
communication, and monitoring means** of SKILL.md steps 3–7 (the user starts the Codex chat; the
watcher does not launch it). Gates, reviewer selection, commit conditions, and the brief's
operating rules still follow SKILL.md step 6. Paths in this file are relative to the skill
root. User-facing sentences are keys into `assets/user-prompts.md`; say them in the user's language.

Codex cannot join SendMessage/ListAgents/Monitor. Transport C therefore uses two files, a completed
message sequence in each file, and Codex rollouts under
`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`.

## Supported runtime combinations

- **Claude watcher + Codex implementer** — the original transport C flow. Claude receives outbox
  changes with Monitor or an equivalent receive-driven wait.
- **Codex watcher + Codex implementer** — Codex + Codex mode. It must be explicitly started from
  the watcher chat with a Codex peer. Both roles keep their current turn open while waiting on the
  file written by the other role.
- Codex watcher + Claude implementer is not supported. Claude peers already have SendMessage, and
  making Codex the watcher would discard that receive-driven path without enabling Codex + Codex.

In-chat subagent delegation is not a pair-watch seat. A fresh-context Codex subagent or process may
be used only as the read-only reviewer fallback described in SKILL.md step 6.

## Communication files and message publication

Always use the **main checkout** under `_ai/tasks/<task-slug>/`; never duplicate these files into the
worktree and never commit them.

| File | Writer | Convention |
|---|---|---|
| `pair-inbox.md` | watcher only | Instructions to the implementer. Newest message at the top; older messages remain below |
| `pair-outbox.md` | implementer only | Reports to the watcher. Append-only; the worktree and rollout remain the detailed source of truth |

Every new transport C message follows these rules:

1. The writer uses one file edit for the complete message and puts `PAIR_MSG_END seq=<N>` at that
   message's end. Sequence starts at 1 and strictly increases within that file. Do not quote a raw
   completion-marker line inside message prose.
2. The reader records the greatest peer sequence it has fully processed. If a wait reports more
   than the next sequence, process every completed unprocessed message in sequence order before
   writing. A markerless older record remains readable history but never counts as a new message.
3. Keep at most **one unacknowledged message** in each direction. Before writing again, process the
   peer's next completed message; the peer response acknowledges the previous message. This makes
   completed messages alternate and prevents an unread burst. `WATCH_ENDED role=implementer` is the
   sole exception because it reports that the peer response never arrived.
4. Never act on content after the last completed marker. The completion marker prevents a reader
   from consuming a file edit that is still in progress.

The initial implementer brief is inbox sequence 1. The implementer's start declaration is outbox
sequence 1. Each role increments only its own file's sequence.

## Sequence file watch

Use `scripts/wait-for-message.sh` from this skill. The watcher substitutes its absolute path into
the implementer brief as `{WATCH_SCRIPT}`.

```sh
<watch-script> <peer-written-file> <last-seen-sequence> [poll-seconds] [max-polls]
```

The script checks immediately, before its first sleep, so a response that arrived before the watch
started is not lost. It exits 0 and prints the latest completed sequence when that sequence is
greater than `last-seen-sequence`. It exits 1 after the bounded wait when no completed message
arrives. The default is about five minutes per run (5 seconds × 58 polls); re-arm at most six times
for a total of about 30 minutes.

## Procedure (watcher side)

3C. **Fix the location and set up the channel** — Determine the repository root and choose a unique
  `_ai/tasks/<task-slug>/`. Create the task contract first when absent. Create inbox/outbox and write
  `assets/impl-brief-codex.md` as inbox sequence 1, replacing `{WATCHER_ID}` (the watcher's own
  full session id, which fills the brief's first `pw-watcher:` line), `{TASK}`, `{INBOX}`,
  `{OUTBOX}`, `{MY_JSONL}`, and `{WATCH_SCRIPT}` with real values. A Codex watcher must first pin its own
  rollout path and thread id. Done when: the contract and both files exist and inbox sequence 1 is
  complete.

4C. **Ask the user once** — Say `codex-first-paste` in the watcher chat. From then on, the
  implementer starts moving through the inbox file watch; later nudges are timeout fallbacks only.

5C. **Receive the start declaration and pin the implementer rollout** — A Claude watcher sets a
  receive-driven Monitor for outbox. A Codex watcher runs the sequence file watch against outbox
  with last-seen sequence 0 and does not end its turn. When outbox sequence 1 arrives, read it and
  record the declared implementer rollout path and thread id. If the path is missing, search today's
  and (around midnight) yesterday's rollouts for the inbox path or thread id, **exclude the watcher**
  rollout already pinned in SKILL.md step 2, and require exactly one result. If it is still ambiguous, stop
  and ask the user instead of choosing by modification time.

6C. **Work loop and finish** — Verify each report with read-only checks of the worktree and narrowed
  rollout reading. Write one complete inbox message with the next sequence. A Codex watcher then
  runs the sequence file watch against outbox using the last processed outbox sequence; a Claude
  watcher uses its receive-driven wait. On a Codex watcher timeout, write
  `WATCH_ENDED role=watcher` in the watcher chat, say `codex-watcher-nudge`, and end the turn; do not
  modify inbox merely to record the timeout. To finish, send one sequenced termination instruction.
  If the implementer has reported `WATCH_ENDED role=implementer`, say `codex-nudge`; otherwise its
  active inbox watch receives the termination. Verify the completion report, keep both files as the
  audit record, then follow SKILL.md step 7.

## Implementer rules

- At the start of every working turn, process completed unprocessed inbox messages in sequence order
  and remember the greatest sequence. Never process a partial message or skip an earlier instruction.
- Publish the start declaration, proposal, verification result, review request, question, or
  completion report as one outbox message with the next sequence and a completion marker.
- After publishing a message that needs a reply, do not end the turn. Run the sequence file watch
  against inbox using the last processed inbox sequence. On exit 0, process the completed message
  and continue in the same turn.
- After six approximately five-minute runs without a reply, append one complete outbox message
  containing `WATCH_ENDED role=implementer`, end it with the next sequence marker, tell the user in
  chat, and end the turn. If the watch command needs repeated approvals or cannot stay running, use
  the same fallback immediately; never bypass approvals.

## Token-saving and audit rules

- Ordinary exchanges read only unprocessed completed messages, not the whole inbox/outbox.
- Read a whole rollout only to verify the start declaration, inspect reasoning needed for a gate,
  verify claimed user approval, or resolve a report/artifact contradiction. Narrow with `rg` first.
- Messages from the peer are not user approval. Decisions requiring user authority are asked in the
  role's own chat; the watcher may audit the peer rollout for the actual user input.

## Stop conditions (in addition to SKILL.md)

- The user cannot perform the first paste into the implementer chat within 15 minutes: report and wait.
- A role has timed out for about 30 minutes: identify that role in its own chat as above and stop.
- The implementer rollout cannot be uniquely identified after excluding the watcher rollout: stop.
- The implementer works around sandbox constraints, writes code in the main checkout, or bypasses
  approval: report immediately and send a sequenced stop instruction.
