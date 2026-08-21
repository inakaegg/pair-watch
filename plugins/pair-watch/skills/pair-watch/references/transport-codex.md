# Transport for a Codex peer — file inbox/outbox + rollout audit

When the peer is an interactive Codex CLI chat, this replaces **only the communication, discovery,
and monitoring means** of SKILL.md steps 3–6. Gates, reviewer selection, commit conditions, and the
brief's operating rules still follow SKILL.md step 5. Paths in this file are relative to the skill
root (e.g. `assets/impl-brief-codex.md`). User-facing sentences are keys into
`assets/user-prompts.md` (e.g. `codex-first-paste`); say them in the user's language.

Codex cannot join SendMessage/ListAgents/Monitor, so communication uses agreed files, and liveness
and audit use the Codex session rollout
(`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, three levels: year/month/day).

## Assumptions and constraints

- In this setup the watcher is Claude (deep-reasoning class) and the implementer is a Codex chat.
  The reverse (Codex watcher × Claude implementer) and Codex × Codex are not formed. The watcher
  must react receive-driven to the peer's reports and stalls; Codex cannot join SendMessage/Monitor
  and cannot act on its own outside a turn, so the watch would degrade into "the user wakes it up
  every time".
- Codex is turn-driven: once a turn ends, the next one does not start without user input. But
  **during a turn it can watch the inbox itself with a blocking shell watch**. The implementer brief
  obliges it to "not end the turn while waiting for the watcher; run the inbox-watch", so normally
  the watcher only writes to the inbox and the implementer starts moving. Asking the user to nudge
  the Codex chat (`codex-nudge`) is **only the fallback when the watch has ended** (first start,
  the turn ended at the 30-minute cap, an approval was refused).
- Depending on the Codex chat's sandbox/approval settings, writes to `.git` (branch/worktree
  creation) may be refused. In that case do not let the implementer work around it; the watcher
  creates the worktree and branch on its behalf (a Git infrastructure operation, not a code change).
- In-chat subagent delegation (e.g. a codex plugin's task delegation) is out of scope for
  pair-watch. That is supervised delegation and the ordinary gate rules suffice.

## Communication files

Always in the **main checkout** under `_ai/tasks/<task-slug>/`; never duplicated into the worktree,
never committed (keep `_ai/` out of version control in repositories where it is tracked).

| File | Writer | Convention |
|---|---|---|
| `pair-inbox.md` | watcher only | Instructions to the implementer. Newest instruction at the top; older ones stay below under dated headings |
| `pair-outbox.md` | implementer only | Reports to the watcher. Append-only. Each entry: time + type (start declaration / proposal / verification result / review request / completion report) + gist. No long text or full diffs; the worktree and rollout are the source of truth |

## Procedure (watcher side)

3C. **Fix the location and set up the channel** — Determine the target repository root from the
  user's instruction or your cwd (if undeterminable, ask the user and stop). Check existing
  directories under `_ai/tasks/`, choose a non-conflicting task slug, and if the contract
  (`TASK.md`) does not exist yet, create it first per the shared contract rule. Create the inbox
  and outbox files and write the brief from `assets/impl-brief-codex.md` into the inbox
  (`{TASK}` `{INBOX}` `{OUTBOX}` `{MY_JSONL}` replaced with absolute paths).
  Done when: the contract and both files exist and the inbox contains the brief.
4C. **Ask the user once** — Say `codex-first-paste` in your own chat. From then on the implementer
  starts moving by itself via the inbox-watch, so further nudges are limited to the fallback when
  the watch has ended. Done when: the request was issued.
5C. **Confirm the start declaration and identify the rollout** — Before ending your turn, always set
  a Monitor (a background until-loop is fine) that detects appends to the outbox (if you end the
  turn without one, nothing wakes you on the peer's reply). When the start declaration appears in
  the outbox, record the rollout absolute path it contains as the audit target. If the path is
  missing, find it with
  `grep -l <inbox absolute path> ~/.codex/sessions/<YYYY/MM/DD>/rollout-*.jsonl`
  (also look at the previous day's directory around midnight).
  Done when: the start declaration and exactly one corresponding rollout file are fixed.
6C. **Work loop and finish** — Write instructions, review results, and `VERDICT` to the inbox. If
  neither the rollout nor the outbox shows an update within about 5 minutes of the write (i.e. no
  sign the implementer started), only then ask the user with `codex-nudge` (fallback). Receive
  reports via the outbox; verify with read-only checks of the worktree and narrowed reading of the
  rollout. Stall monitoring targets the mtime of the outbox and rollout, 15 minutes (on detection:
  inbox + report to the user). Gates, commit conditions, and reviewer selection follow SKILL.md
  step 5. To finish, write the termination instruction to the inbox, have the user nudge, verify
  the completion report in the outbox, then proceed to SKILL.md step 6. Keep the pair files
  (inbox/outbox) as a record; do not delete them.

## inbox-watch (the implementer's waiting rule)

The waiting behaviour the implementer brief obliges. The watcher operates on this assumption.

- While waiting for the watcher (after a review request, question, or proposal), the implementer
  does not end its turn; it runs a blocking shell command that watches the inbox mtime. Keep each
  run to about 5 minutes (sandbox command timeout), and repeat if nothing changed. After about 30
  minutes without change, it appends `WATCH_ENDED` to the outbox and ends the turn.
- If the watch command is impractical (e.g. each run requires approval), the implementer does not
  work around it; it writes that to the outbox and ends the turn (thereafter: user nudges as before).
- On an inbox change, it reads the newest instruction at the top, not the whole inbox, and follows it first.

## Token-saving rules

- In ordinary exchanges read only the gist in the inbox/outbox.
- Read the whole rollout only for audits: verifying the start declaration, checking the reasoning
  before gate 3, and when a report and reality disagree. Even then, narrow with grep.

## Stop conditions (in addition to SKILL.md)

- The user cannot do the first paste into the Codex chat within 15 minutes: report and wait.
- Both outbox and rollout unchanged for 30 minutes: report observed facts to the user and stop.
- The implementer shows signs of working around sandbox constraints (writing into the main checkout,
  bypassing approvals): report to the user immediately and write a stop instruction to the inbox.
