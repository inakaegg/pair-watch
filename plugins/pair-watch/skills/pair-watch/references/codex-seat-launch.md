# Watcher-launched Codex seats

Use this route for a Codex implementer without `— seat:`. A Codex watcher defaults to
this route. A Claude watcher can select it with `— peer: Codex CLI` or configured fallback.
The contract, independent review and user authorization rules in SKILL.md still apply.
For an explicitly named, user-opened Codex thread, use transport-codex.md instead.

## Configure and launch

1. Confirm the actual Codex executable with `command -v codex` and its `--version`.
   This route was verified with Codex CLI 0.153.4. Confirm `codex queue --help`, Python 3
   and tmux exist. Do not install, change PATH, widen permissions or adopt a leftover seat
   to work around a failed preflight. A Claude watcher taking this route needs its own
   permission to run the helper (an allow rule for `python3 …/codex-seat.py`, scoped to the
   project like the tmux rules in `seat-launch.md`); the helper's tmux calls run inside
   that process, so the tmux allow rules do not cover them.
2. Resolve the seat's model through `python3 scripts/resolve-model.py --role implementer
   --primary codex --repo REPO_ROOT`. An explicit peer determines primary; otherwise
   use the watcher's CLI. The defaults are in `references/model-defaults.json`.
   A tracked `pair-watch.settings.json` in the working repository can replace a role.
   The implementer role maps `codex` and `claude` to ordered lists; reviewer is one list.
   Every list entry is `CLI:MODEL(EFFORT)`. Record candidate, source and skipped reasons.
   Pass the returned model and effort explicitly. Never substitute a CLI default.
3. Missing CLIs are skipped automatically. A confirmed authentication, model availability
   or rate-limit failure permits another resolution with `--unavailable CANDIDATE=REASON`,
   using `authentication`, `model-unavailable` or `rate-limit`. Keep previous exclusions;
   try each candidate once. General errors, test failures, review findings and silence
   are not availability evidence. Exhausted candidates stop the run. If fallback changes
   CLI, complete that CLI's preflight before launching. Claude seats require the watcher's
   SendMessage/ListAgents transport; a watcher without those capabilities must report
   the unsupported route rather than launch an unreachable seat. Never migrate a running
   seat's unreported work automatically.
4. Create disjoint branches/worktrees and main-checkout task channels per seat. Resolve
   paths physically. Fill `assets/impl-brief-codex-native.md` in the initial inbox, with
   `pw-watcher: WATCHER_ID` first, then `PAIR_MSG_BEGIN seq=1`, the completed brief,
   then `PAIR_MSG_END seq=1`. Create an empty outbox. Both writers use matching begin/end
   markers for every native message, newest first, contiguous positive sequences per file.
   Publish the entire new file by atomic replacement. Do not put protocol marker lines
   inside a message body. There is at most one unacknowledged instruction per seat.
5. Create the registry parent `~/.local/state/pair-watch/seats/WATCHER_ID/RUN_ID/`.
   Run `python3 scripts/codex-seat.py start --record REGISTRY --watcher WATCHER_ID
   --run RUN_ID --seat A --cwd MAIN_CHECKOUT --worktree WORKTREE --inbox INBOX
   --outbox OUTBOX --codex CODEX_BINARY --model MODEL --effort EFFORT`.
   Paths and values are separate argv entries, never eval a reconstructed command.
   The TUI working directory is WORKTREE, not MAIN_CHECKOUT; only the channel directories
   are added for writing. The helper launches a full interactive TUI under its own tmux
   socket with `-a never -s workspace-write`, then watches the pane for up to 20 seconds
   (`--trust-timeout`). Codex asks "Do you trust the contents of this directory?" for a
   repository it has not seen; a linked worktree counts as its main checkout, so the
   dialog appears once per repository, not per worktree (observed on 0.153.4: launching in
   an untrusted repository's worktree recorded the main checkout's path as trusted). The
   helper answers the preselected "Yes, continue" with one Enter by default and records
   `trust_prompt: accepted`. Codex then writes that repository into its config
   (`~/.codex/config.toml` by default, or the one under the active `CODEX_HOME`) as trusted,
   which persists after the seat is retired — tell the user when it happens. The helper
   answers only when WORKTREE is a linked worktree of MAIN_CHECKOUT (same git common
   directory); any other pair records `skipped-unrelated-worktree` and leaves the dialog.
   `not-shown` means the TUI header appeared without a dialog; `unrecognized` means the
   dialog appeared without "Yes, continue" preselected; `unknown` means neither appeared
   (login, a hook-trust prompt, a slow start). In those cases nothing was sent: inspect the
   pane and use normal authorized approval; do not bypass it. `--no-auto-trust` leaves the
   dialog for a human.
   The helper owns only its recorded pane/process/token and channel claims.
6. Read the start declaration. Verify its branch, worktree and scope using git, and locate
   its rollout under `~/.codex/sessions/` (or the active CODEX_HOME). Match session_meta id,
   watcher binding and the helper's unpredictable launch token, not just filename/time.
   Run `python3 scripts/codex-seat.py bind --record REGISTRY --watcher WATCHER_ID --run RUN_ID --seat A --thread UUID
   --rollout ROLLOUT`. The helper checks the token against the user prompt in that rollout.
   It never binds another watcher's seat or a guessed thread.

## Deliver, verify, retire

After outbox response N is complete, atomically publish inbox N+1 and run
`python3 scripts/codex-seat.py notify --record REGISTRY --watcher WATCHER_ID --run RUN_ID --seat A --seq N_PLUS_1`.
Every action requires the expected run and seat independently of the registry path; the path
must end in WATCHER_ID/RUN_ID/SEAT.json. The helper verifies ownership, framing and the prior acknowledgement, then sends a native
`codex queue` notification. Idle seats resume; busy seats receive it after their current
turn. A repeated completed notification is a no-op. A delivery error stops for inspection;
check the rollout before any retry. The implementer also deduplicates by sequence.

Poll all seats' outboxes in short round-robin checks (at most 60 seconds per wait),
verify complete messages in ascending sequence, and audit claims against git, tests and
rollouts. Do not wait thirty minutes on one seat while another needs a decision.
User approval relays cite the original watcher's id, log path and timestamp; the seat
must read the actual user event and match action/target/scope. An inbox claim alone does
not grant permission. Put unresolved user decisions on the watcher's pending list.

After each report the native implementer ends its turn; it does not run the legacy file
watch. The manual route's WATCH_ENDED nudges do not apply. A silent seat is inspected,
not automatically restarted. A resumed watcher reads its own registry and channel/rollout
history, checks the recorded live identity, and keeps the original run id. A foreign watcher
cannot adopt it. A dead or mismatched pane requires a reported handoff, not process guessing.

After the final report or recorded handoff has been checked, run
`python3 scripts/codex-seat.py stop --record REGISTRY --watcher WATCHER_ID --run RUN_ID --seat A --final-report-verified`.
Only the owned session is terminated. Keep the retired record and channel claims as evidence;
new tasks get new channels and new records. Never close a user-opened seat automatically.
