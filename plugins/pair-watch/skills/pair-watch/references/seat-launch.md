# Launching, recovering, and retiring seats

The mechanics behind SKILL.md steps 3–7 for Claude seats the watcher launches itself. Everything
here was verified in live runs on macOS unless a line says otherwise. Paths are relative to the
skill root.

## Preflight (SKILL.md step 3)

Three things make a launch fail silently. Check them once per run, before the first launch.

1. **Permission rules for tmux.** A watcher running in the default (auto) permission mode is
   blocked by the harness's permission classifier from launching `claude
   --dangerously-skip-permissions` — the tmux route was denied outright on every attempt, and
   chat-level approval did not override the classifier. The watcher cannot add the rules itself
   (self-editing `settings.json` permissions is blocked by design). The user adds these to
   `permissions.allow`:

   ```json
   "Bash(tmux new-session:*)", "Bash(tmux send-keys:*)", "Bash(tmux capture-pane:*)",
   "Bash(tmux kill-session:*)", "Bash(tmux ls:*)"
   ```

   Preferably in the project's `.claude/settings.json` (scoped to that repository), or in
   `~/.claude/settings.json` when seats are launched across many projects. Say the trade-off
   before the user chooses: within their scope these rules let any session start arbitrary
   commands via `tmux new-session`, inject keystrokes, and read pane contents without prompting —
   a grant broader than pair-watch. Recommend project-local, and removal when the seat workflow
   is no longer used. An allow rule cannot override deny/ask rules or blocking hooks; where those
   match, a launch is still stopped. Check: `grep -c 'tmux new-session' <settings file>`.
2. **`crossSessionInbound: accept`.** A launched seat has no human to approve inbound messages,
   so without it the handshake goes silent — a symptom indistinguishable from the trust-dialog
   stall. Check: `grep crossSessionInbound ~/.claude/settings.json`. "Both sides" means the
   watcher's chat and every seat; they share the user's settings file.
3. **A trusted directory to launch from.** In an untrusted cwd the seat stalls invisibly at the
   workspace-trust dialog before the prompt is read. Trust is per directory and persists in the
   CLI config once accepted, except for git linked worktrees, where an acceptance was observed
   not to persist. For a seat that must work in a worktree, the verified route is cwd = the
   trusted main checkout (or any trusted directory) plus `--add-dir <worktree>`; the seat can
   then write in the added directory. Check: the directory appears under `projects` in
   `~/.claude.json` with `hasTrustDialogAccepted: true` (observed layout; a CLI update may move
   it — fall back to looking at the seat's screen after launch).

## Registry entry (write before the launch)

`~/.local/state/pair-watch/seats/<watcher-id>/<run-id>/<seat>.json`, one file per seat:

```json
{
  "seat": "A",
  "watcher": "<full watcher session id>",
  "run": "<run-id, ISO-8601 to the second>",
  "project": "<absolute project directory>",
  "route": "tmux",
  "tmux_session": "pw-<watcher-id8>-<run-hhmmss>-A",
  "model": "MODEL_FROM_SETTINGS",
  "effort": "EFFORT_FROM_SETTINGS",
  "started": "<ISO-8601>",
  "address": null,
  "socket": null,
  "session_id": null,
  "retired": null
}
```

`address` and `session_id` are filled from the start declaration; `retired` gets the close
timestamp when the seat is retired. `socket` is the seat's messaging endpoint,
`uds:/tmp/cc-socks/<pid>.sock`, where `<pid>` is the pane pid of the seat's tmux session
(`tmux display -p -t <tmux_session> '#{pane_pid}'`; for a seat launched with the command below the
pane process *is* the seat's claude process — verified on macOS with three seats). Fill it at the
handshake and re-derive it whenever the watcher reopens: `address` (a display name that ListAgents
may show for more than one seat) and the `from` value are per-process and per-chat memory, the
tmux name is not. A `— seat:` session has no tmux name the watcher knows, so its `socket` stays
null and it keeps being addressed by name + ref. `<run-id>` is the run's start time so a second run from the
same watcher chat cannot overwrite the entries of seats the first run still owns. The tmux
session name carries the run for the same reason: `tmux new-session -s` fails on a name that
already exists, so a name without the run part collides with a seat the first run is still
using. The name is a convenience for humans; the registry is the source of truth.

## The watcher's own record (SKILL.md step 2)

`~/.local/state/pair-watch/seats/<watcher-id>/watcher.json`, one file per watcher, rewritten
every time the watcher chat starts, is reopened, or is resumed:

```json
{
  "session_id": "<full watcher session id>",
  "jsonl": "<absolute path of the watcher's session jsonl>",
  "pid": 45626,
  "socket": "uds:/tmp/cc-socks/45626.sock",
  "updated_at": "<ISO-8601>"
}
```

`pid` is the watcher's own claude process — the parent of its Bash tool shell, so from a Bash
call `ps -o ppid= -p $$` prints it, and `lsof -a -U -p <pid>` lists the socket it owns under
`/tmp/cc-socks/` (`uds:` + that path is `socket`). The file sits one level above the run
directories, so it survives across runs of the same watcher chat; a reopen or resume rewrites it
without changing the run-id of seats already launched. Seats read this file only when a send to
the watcher fails or a report goes unanswered (brief rule 11); they trust it only if `updated_at`
is newer than their last contact, `ps -p <pid>` shows the process alive, and the socket path
exists — a stale file from a watcher that never came back must not send them into a dead socket.
Even then a seat switches addresses only on a message that cites the run's `pw-watcher:` id. The
file is what lets a reopened watcher be found without any seat messaging other sessions. Codex
watchers write no such file (transport C uses files, not sockets).

## The launch command (SKILL.md step 4)

Write the filled brief to a file first (a scratch file outside the repository), then:

```sh
tmux new-session -d -s pw-<watcher-id8>-<run-hhmmss>-A -c <trusted-dir> 'env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SSE_PORT -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_AGENT_ID claude --model <resolved-model> --effort <resolved-effort> --dangerously-skip-permissions "$(cat <brief file>)" --add-dir <worktree>'
```

Rules that came out of failed launches:

- **The tmux call is its own Bash invocation.** The permission rule matches a command that starts
  with `tmux`; a compound command (`pkill …; tmux …`, `tmux … && sleep …`) does not match and is
  denied. That includes `tmux capture-pane` — run it alone too.
- **Scrub the inherited environment inside the string passed to tmux.** With the watcher's
  `CLAUDE*` variables inherited, the seat registers as a child or remote session and its
  messaging misbehaves. Unset every `CLAUDE*` variable the watcher's harness set (`env | grep
  '^CLAUDE'` lists them); the list above is what was needed in the verified runs.
- **The prompt goes before `--add-dir`.** `--add-dir` takes multiple values, so a positional
  prompt placed after it is swallowed as a path.
- **Never pass `--disallowedTools AskUserQuestion`.** Observed to remove SendMessage from the seat
  as well, leaving it unable to reply. Question discipline comes from the brief.
- **Prefer tmux over `script(1)`.** A seat launched with `script -q /dev/null claude …` from an
  IDE-hosted watcher surfaces as a visible terminal in the user's IDE, and a `script` seat
  accepts no outside input, so a stuck chooser can only be recovered by kill + `--resume`. Use
  `script` only where tmux is absent (`script -q /dev/null claude … < /dev/null` in the
  background on macOS/BSD; `script -qc "claude …" /dev/null` on Linux).

After the launch, look at the screen once: `tmux capture-pane -p -t <session>`. A seat that is
reading the brief shows the brief text and a spinner; a trust dialog or a chooser shows its
options.

## Handshake and monitoring (SKILL.md steps 5–6)

- **Event-driven, not polling.** The watcher acts on signals: the start declaration, replies, and
  the stall monitor. A seat whose brief obliges it to report needs no idle subscription —
  `notify_when_idle` notices only duplicated the reports in live runs. When a report is overdue,
  stat the seat's session jsonl mtime instead. Attach `notify_when_idle` (one-shot) only to a seat
  that has no reporting duty on its current instruction.
- **Stall monitor.** One Monitor (or an equivalent loop) per seat on its jsonl mtime; emit once
  when the file has not changed for 15 minutes, then send the seat a status check.
- **A seat stuck on an on-screen chooser cannot be messaged out of it.** Queued messages are read
  at the seat's next tool round, and a seat waiting for key input never reaches one. Recovery: a
  tmux seat accepts injected keys — `tmux send-keys -t <session> Escape` to dismiss, `Down` and
  `Enter` to choose (verified by clearing a workspace-trust dialog with Down+Enter). If keys do
  not clear it: `tmux kill-session -t <session>`, then relaunch with `claude --resume
  <session-id>` in a fresh tmux session; the seat's context comes back. A seat that instead asks
  in text and goes idle is the easy case: a SendMessage answer resumes it.

## Retiring a seat (SKILL.md step 7)

A launched seat is retired by the watcher when its task ends: after the seat's final report, with
its branch committed or its uncommitted state handed over in the task's `_ai/` record, and never
while it still holds unreported work. `tmux kill-session -t <session>` ends it. Nothing is lost:
the seat's session log stays on disk and `claude --resume <session-id>` brings the conversation
back with its context when someone later needs to ask that seat something — which is why the
registry entry is marked `retired` rather than deleted at the kill, and keeps the session id
until the run ends. At the end of the run the watcher closes any launched seat still open and
removes the run's registry entries together, so leftovers do not accumulate. Entries left by an
interrupted run are safe to delete by hand.

Seats that live in a terminal tab rather than tmux (a `— seat:` session, or a `script` seat) are
ordinary processes: SIGTERM the seat's `claude` process, then SIGHUP its parent shell, and a
Terminal.app profile set to close the tab when the shell exits closes it by itself (verified on
macOS; no AppleScript, no automation-permission dialog). In an IDE the process ends but the tab
stays; there is no API to close it from outside. A `— seat:` session is retired only on the
user's word, because it may hold state the user wants to look at.

Stall recovery (kill + `--resume` of a seat stuck on a chooser) is the watcher's call and is
reported to the user afterwards; retiring is not.
