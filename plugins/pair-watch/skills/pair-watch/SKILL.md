---
name: pair-watch
description: >-
  Use to run a coding task as a supervised pair from one chat. The chat that invokes it becomes
  the read-only watcher; it launches one or more implementer sessions itself (real CLI sessions
  under tmux, each with its own model and effort), delivers their role briefs, verifies their
  reports against git, tests and their session logs, and runs the review gates. The user types
  "/pair-watch:pair-watch TASK" in one chat only. Japanese cues: 「並行体制で」「pairで」
  「席を立てて」「実装席を起動して」. Options on the same line: "— seat: NAME" to use a session
  the user already opened instead of launching one; "— peer: Codex CLI" for a Codex implementer
  (file inbox/outbox + rollout audit; started from a Codex chat, another Codex chat can be the
  implementer). Not for solo work or in-chat subagent delegation.
metadata:
  language: en
  tested-with: "Claude Code (SendMessage/ListAgents/Monitor, tmux-launched sessions on macOS), Codex CLI 0.153.4 native queue and legacy file watch and rollout layout ~/.codex/sessions/YYYY/MM/DD/"
---

# Pair-watch — a supervised pair launched from one chat

The user types `/pair-watch:pair-watch <one-line task>` in **one** chat. That chat is the
**watcher**. It fixes the task and the seats, launches each implementer seat as a real CLI
session, delivers the seat its role brief (from `assets/`), verifies every report against the
artifacts, runs the review gates, relays the user's decisions, and retires the seats when the
task ends. The watcher never edits source. Its writes are the task contract, inbox messages, initialization of empty outboxes,
seat registries and channel ownership records, and worktrees or branches created on seats' behalf.
After initialization, only each implementer writes its outbox.

Seat selection follows the invoking CLI unless `— peer: Codex CLI` selects Codex.
Codex seats without `— seat:` are launched under tmux and notified through native
`codex queue`; follow `references/codex-seat-launch.md` for steps 3–7. This supports
Codex + Codex without Claude. Claude seats use `references/seat-launch.md` and SendMessage.
An explicitly user-opened Codex `— seat: <thread UUID>` keeps the legacy file-watch route
in `references/transport-codex.md`. A Claude `— seat: <name>` uses its ListAgents address.

Model, effort and ordered fallback candidates live in `references/model-defaults.json`,
overridden by the repository's tracked `pair-watch.settings.json`. Resolve with
`python3 scripts/resolve-model.py --role implementer --primary CLI --repo REPO_ROOT` before launch.
The model selection and availability rules in `references/codex-seat-launch.md` apply to
both CLIs. `— implementer: <model>(<effort>)` is an explicit user override for that run;
record it and do not invent additional fallback candidates for it.

## Language (read first)

- **Output language**: write everything the user or a seat will read — contracts, briefs'
  task lines, inbox/outbox entries, questions, completion reports — in the language of the task
  description. If that is ambiguous, use the language the user last wrote in.
- **Briefs**: use the templates in `assets/` as they are (English). Do not rewrite them ad hoc.
- **Protocol tokens** (below) are fixed strings. Never translate or paraphrase them.

## Protocol tokens (language-neutral, never translate)

| Token | Who writes it | Meaning |
|---|---|---|
| `VERDICT: LGTM` / `VERDICT: CHANGES REQUESTED` | gate reviewer | gate result; a local commit is allowed only after `VERDICT: LGTM` |
| `[AGENT-DECISION]` | implementer | marks a design decision that came from neither the user nor observed data (the Japanese kit's `[エージェント判断]` is the same tag; both forms are accepted) |
| `PAIR_MSG_END seq=<N>` | transport C writer | completes one message; sequence is positive, strictly increasing per file |
| `WATCH_ENDED role=implementer` | Codex implementer (outbox) | inbox file watch stopped after ~30 min; nudge the implementer chat |
| `WATCH_ENDED role=watcher` | Codex watcher (own chat) | outbox file watch stopped after ~30 min; nudge the watcher chat |
| `pair-inbox.md` / `pair-outbox.md` | watcher / implementer | transport C files under `_ai/tasks/<slug>/` in the main checkout |
| `pw-watcher: <watcher session id>` | watcher (brief's first line) | binds the seat to the watcher that sent the brief; stays first so it lands in the seat's own session record |
| `watcher.json` | watcher (registry) | the watcher's own current address record (`~/.local/state/pair-watch/seats/<watcher-id>/watcher.json`); rewritten every time the watcher chat starts, is reopened, or is resumed; read by seats when a send to the watcher fails |
| `{WATCHER_ID} {TASK} {MY_ADDR} {MY_JSONL} {INBOX} {OUTBOX} {WATCH_SCRIPT}` | brief sender | placeholders that must be replaced before sending |

## Procedure

1. **Fix the task, the seats, and the options** — Parse the invocation line. No task → say
   `ask-task` (`assets/user-prompts.md`) and stop. Select the route and settings above.
   Native Codex seats follow `references/codex-seat-launch.md`; user-opened Codex seats
   follow transport C. All routes write the contract before launching or messaging.
   Decide one seat per independent partition with disjoint branches, worktrees and files;
   use one seat when the task does not
   split. Reply in your own chat with one line per seat (label, scope, model and effort) and the
   model your own chat runs as. Done when: task, seats, and transport are stated in your chat.
2. **Locate your own session log and address** — Claude: build and confirm
   `~/.claude/projects/<slug>/$CLAUDE_CODE_SESSION_ID.jsonl`; the id is `<watcher-id>`, and the
   current time (ISO-8601, to the second) is `<run-id>`. Call ListAgents once: its first line
   names this session ("This session is <name> [<ref>]"); that name is `{MY_ADDR}`, the address
   seats send their messages to — pass it with the `[<ref>]` when the same name appears more
   than once in the listing, so a seat's reply cannot land in another session. Codex: find and confirm the current rollout under
   `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` and record its thread id. Claude watcher only:
   then write (or rewrite) `~/.local/state/pair-watch/seats/<watcher-id>/watcher.json` with your
   session id, jsonl path, process id, and messaging socket (`references/seat-launch.md`, "The
   watcher's own record") — this is what seats fall back to when a send to `{MY_ADDR}` fails, so
   it is written before any seat exists and again on every reopen or resume of this chat. A Codex
   watcher has no messaging socket and writes no such file; transport C seats never read one.
   Done when: the path is confirmed to exist and the address is known (and, for a Claude
   watcher, `watcher.json` is current).
3. **Contract and preflight, before the first launch** — Write the task contract
   (`_ai/tasks/<slug>/TASK.md`, Shared rules below) if it does not exist; this happens on every
   route. For a code-changing task with launched seats, create the task branch and worktree
   now, on the seat's behalf, so the launch can point `--add-dir` at it; the brief then states
   that they exist. For a `— seat:` run the seat creates them itself (brief rule 1), and for a
   Codex seat the selected native or manual reference takes over from here.
   Then, once per run for launched Claude seats, check the three things a launch silently fails
   without (details and the check commands: `references/seat-launch.md`): the tmux allow rules
   in the user's `permissions.allow`; `"crossSessionInbound": "accept"` in
   `~/.claude/settings.json`; a trusted directory to launch from (a seat that works in a git
   worktree is launched from the trusted main checkout with `--add-dir <worktree>`). If a rule
   is missing, say `spawn-permissions` and stop until the user adds it — the watcher cannot add
   permission rules itself, and chat-level approval does not override the classifier. The three
   checks are skipped for a `— seat:` run and for a Codex seat. Done when: the contract exists,
   and the checks are confirmed or the user has been told what is missing.
4. **Launch the seats** — For each seat: write the registry entry, name the tmux session
   `pw-<watcher-id8>-<run-hhmmss>-<letter>`, fill the brief (`assets/impl-brief.md`; `{WATCHER_ID}`
   is your full session id and the `pw-watcher:` line stays first; `{MY_ADDR}` is the name from
   step 2; `{MY_JSONL}` is your log path), and launch with the command in
   `references/seat-launch.md`. The tmux call is its own Bash invocation, never part of a
   compound command, and the env scrub sits inside the string passed to tmux. Then look at the
   screen once (`tmux capture-pane`) to confirm the seat is reading the brief. For `— seat:
   <name>`: skip the launch, send the brief by SendMessage to that name with the last paragraph
   replaced as the asset notes (a human may be watching that chat), and if ListAgents does not
   list the name say `seat-not-found` and stop. Done when: every seat's process is up, or the
   named seat has been messaged.
5. **Handshake** — Each seat replies with a start declaration (branch and worktree, scope,
   approach, its session jsonl path). Copy the `from` address of that reply verbatim; it is the
   seat's only address from then on. Record the address and the session id in the registry, and
   for a tmux seat also its `socket`, derived from the tmux session (`tmux display -p -t
   <session> '#{pane_pid}'` → `uds:/tmp/cc-socks/<pane_pid>.sock`); the socket is what survives
   a watcher restart: the address you copied here stays in this chat's history, but nothing
   guarantees it after either side has restarted (observed: the watcher's own address changed on
   reopen), so the registry socket, re-derived from tmux, is the value to trust.
   If no declaration arrives within about five minutes, look at the seat's screen: a workspace
   trust dialog, a chooser, or an unread brief are the usual causes, each with a recovery in
   `references/seat-launch.md`; tell the user what you saw and what you do next with
   `seat-silent`. A `— seat:` session that does not answer within 15 minutes is a
   stop condition. Done when: every seat has declared and its branch and worktree are verified
   read-only.
6. **Work loop** — Follow the operating rules of `assets/impl-brief.md` from the watcher's side:
   answer proposals, verify each report with read-only git, grep, and test logs, read the seat's
   jsonl for claims no artifact can prove, and put anything that needs the user on a single
   pending list in your own chat. Gates, reviewer selection and commit conditions: Shared rules
   below. Use project review settings when present; otherwise resolve `--role reviewer`
   with the bundled resolver and the same availability rules. A fresh-context Codex or
   Claude reviewer uses read-only tools and only review artifacts. Disclose fallback in the
   result. A review that ended in tool failure or without a `VERDICT` line does not count as a
   round. While waiting on a seat, do not wait indefinitely on receive: watch the seat's session
   log for a stall (no update for 15 minutes) with Monitor or an equivalent loop, and on a stall
   send a status check. SendMessage delivery can be lost: if the seat's jsonl shows no activity
   within a few minutes of a work instruction, resend the same content (a delivery-loss
   countermeasure, distinct from the 30-minute failure judgement). With a Codex seat, check the
   rollout instead of resending, and use transport C's nudge only when its watch has ended. When
   the user decides something, relay it to the seat explicitly, citing where it is recorded
   (your session jsonl path and a timestamp).
7. **Finish** — Verify the seat's final report against the artifacts. Retire each seat you
   launched once its task ends: after its final report, with its branch committed or its
   uncommitted state handed over in the task's `_ai/` record, never while it holds unreported
   work (`references/seat-launch.md`, "Retiring a seat"). A `— seat:` session is left running
   unless the user says otherwise. Write the completion report in your own chat and remove the
   run's Claude registry entries. Native Codex records remain retired for audit. push, PR, and merge always require the user's explicit permission.

## Seats

- **One watcher, N seats.** The watcher stays single and never implements. Every seat is a full
  interactive CLI session — launched by the watcher, or named by the user — never a subagent
  (a subagent inherits the launching session's reasoning effort and cannot raise it, and its
  result is summarised into the caller's context instead of being verified). Each seat gets its
  own brief with a label (seat A, B, C…).
- **Disjoint scope per seat.** Seats never share a branch, worktree, or source file. Each brief
  states the seat's own scope and the other seats' scopes with the files and branches to avoid.
  Shared files (a ROADMAP, a settings registry) require a one-line check-in with the watcher
  before any seat edits them.
- **One seat, one task — no reuse.** A seat is launched for one task and retired when that task
  ends. The watcher never hands a finished seat a second, unrelated task, however idle it looks:
  its context already holds the previous task, only the human could compact it, and the next
  task would start from a worse position than a fresh session (observed live: a reused seat had
  to be stopped and its work handed over). Follow-up work on the *same* task — review fixes, a
  merge conflict on that branch — stays with its seat. A new task gets a new seat.
- **Seat identity.** Every seat is bound to the watcher that launched it, in two places that exist
  on every route: the `pw-watcher: <watcher-id>` line at the top of its brief, which lands in
  the seat's own session record, and the registry entry the watcher writes at launch
  (`~/.local/state/pair-watch/seats/<watcher-id>/<run-id>/<seat>.json`; fields in
  `references/seat-launch.md`). Before messaging, reusing, or closing any seat, the watcher checks
  its own registry directory; a seat bound to another watcher is foreign — never message it,
  assign it work, or close it, however idle it looks. Exactly two kinds of unbound session may be
  claimed: the session the user named with `— seat:`, and a session the watcher launched and has
  not finished the handshake with. Fresh seats by default: a leftover seat is context already
  spent, not capacity. List leftovers to the user and leave them running.
- **Model and effort.** Resolve explicit values and fallback order from the settings above.
  The watcher is the chat the user already started, so the skill cannot change its model.
  Report the actual watcher model and the resolved seat candidates before launching.
- **What grows with N.** Reviewers are separate processes and run in parallel, so review
  throughput is not the limit. What bounds N: the task graph (seats need disjoint files and
  branches, so N is at most the number of independent tasks ready now), the decisions that queue
  up for the user, and the watcher's own context. Observed in live runs, the watcher's own work
  stays light with four seats and several reviews in flight — it routes messages, launches
  reviewers, and forwards verdicts; the heavy lifting runs elsewhere. Do not add a second watcher
  for load; it splits the audit trail and the pending list for no gain.
- **What to tell the user up front.** Launched Claude seats run with `--dangerously-skip-permissions`;
  invoking pair-watch is the opt-in for that. Decisions that need the user pile up on the
  pending list and are presented at an agreed checkpoint instead of one by one. The
  independence guarantee is per pair (watcher ↔ seat); seats are not independent of each other's
  mistakes when their scopes touch. Long runs should compact the watcher chat at a checkpoint.

## Claude watcher restart and disappearance

For native Codex seats use `references/codex-seat-launch.md`, including after restart.

Two facts drive this section (observed live, 2026-09-04): a session's id and its jsonl survive
closing and reopening the chat, but its messaging address does not — the socket
(`/tmp/cc-socks/<pid>.sock`) and the ListAgents name and ref belong to the process, and every
reopen or `--resume` is a new process. A seat that keeps sending to the old address gets
`ENOENT`, and the watcher that reopens knows none of its seats' current names. Neither side can
derive the other's socket from a session id alone (jsonl records carry no pid, and another
process's environment is not readable on macOS), so the mapping is kept in the registry.

- **Watcher reopened or resumed.** Rewrite `watcher.json` (the `watcher.json` part of step 2
  only — keep the run's existing `<run-id>`; a resume is not a new run, and taking a fresh
  run-id would orphan the seats' registry entries and their tmux names). Then, for every live
  seat in your registry directory, derive its socket from the tmux session name recorded at
  launch (`tmux display -p -t <session> '#{pane_pid}'`; a tmux-launched seat's pane pid is the
  seat's claude process, verified on macOS) and update the entry; a `— seat:` session has no
  tmux name you know, so it keeps its name + ref. Send each seat one message
  whose first line is `pw-watcher: <your session id>` — that line is what a seat checks before
  accepting a new address, whether it is still working or has stopped under rule 11 — followed by
  "the watcher restarted; reply to the `from` of this message from now on" and a one-line status
  request. Rebuild your view from the replies and the task records. Do not search ListAgents by
  name, do not ask any session who it is, and do not treat a seat's silence as failure until
  the stall rules apply. Say `watcher-reconnected` to the user once the replies are in.
- **Watcher gone for good (or long).** Seats are told in their brief what to do (rule 11): when a
  send to the watcher fails or a report goes unanswered for 30 minutes, read `watcher.json`; if
  it is newer than their last contact and its pid is alive, switch to its socket and continue;
  otherwise write their current state into the task record and stop — no commit, merge,
  external request, deletion, or message to any other session. Recovery is the same chat
  coming back — reopened, or `claude --resume <watcher session id>` — which reads those records
  first, then reconnects as above; a seat accepts a new watcher address on exactly one
  condition: the message's first line cites this run's `pw-watcher:` id, and only the original
  chat can write that line truthfully. A different chat cannot take the seats over: they are
  bound to the original watcher's id (Seat identity), and a watcher that starts fresh gets its
  own id and its own registry directory. When the original chat is not coming back, the seats
  stay stopped with their state in the task records; tell the user, who can resume the original
  chat, or retire the seats and launch new ones under a new watcher for the remaining work. A
  seat never goes looking for a watcher.
- **Same-name seats.** Seats launched into the same project get the same ListAgents display name
  (observed: two `ses-scout-f5`). After the handshake the watcher addresses a seat only by the
  `from` it copied or by the registry socket, never by display name; before the handshake a
  name is used only with its `[<ref>]`. A message sent by bare name to a shared name reached the
  wrong seat in a live run (it carried a deletion instruction; the receiving seat noticed and
  refused). The `— seat:` route keeps name + ref, because the watcher does not know that
  session's tmux name.

## Pair-watch or the Workflow tool?

Both run several agents at once; they differ in what the agents are.

- **Pair-watch seats are interactive sessions.** Each seat can be messaged mid-task, nudged when
  its log stalls, given a changed brief, or opened by the user to look at. Each seat carries its
  own model and effort. Reviewers are separate processes, so a different-lineage reviewer (Codex)
  is a first-class choice. Use pair-watch when the work is long, the user may add or redirect
  tasks while it runs, or a seat must hold uncommitted state across several instructions.
- **Workflow agents are subagents driven by a script.** They also take a per-agent `model` and
  `effort`, so separately configured implementers are possible there too. But the agents are Claude
  models only: a Codex reviewer is reachable only when an agent shells out to `codex exec`, and
  no agent is a chat the user can join. Changing course means editing the script and resuming.
  Use Workflow for a batch of same-shaped, pre-scoped work — N translations compared on the same
  phrases, N findings each verified from several lenses — where determinism beats interactivity.
- **Mixing is fine.** A pair-watch seat may run a Workflow inside its own task for a fan-out step;
  the watcher does not.

## Wrong shortcut → correct action

- Search ListAgents or session logs for a chat the user might have opened → Pair-watch does not
  search for sessions. Launch a seat (step 4), or use the name the user gave with `— seat:`.
- Send to a session name or ref after the handshake → Name resolution is unreliable. The `from`
  address of the start declaration is the only address. After a watcher restart that address is
  re-derived from the registry's tmux name ("Watcher restart and disappearance"), not looked up
  by name.
- Look for a lost watcher by messaging the sessions ListAgents shows → A seat reads `watcher.json`
  and either switches to the socket it names or writes its state down and stops. A lost watcher
  is found by the next watcher reading the registry and the task records, not by seats asking
  around.
- Launch a background or in-chat subagent as the implementer → That is solo delegation, not a
  pair-watch seat, and it inherits your effort. Launch a real CLI seat (step 4); a fresh-context
  subagent is allowed only as the read-only gate 3 reviewer fallback of step 6.
- Run the tmux launch inside a compound command (`pkill …; tmux …`) → The permission rule matches
  a command that starts with `tmux`; run the tmux call alone.
- Hand a finished seat the next task → One seat, one task. Retire it and launch a fresh seat.
- Keep trying ListAgents/SendMessage toward a Codex seat → That route does not exist. Switch to
  transport C's file transport.
- Judge a seat failed because it produced no output → Unless there is an explicit error, process
  exit, or misconfiguration, wait at least 30 minutes (the lower bound for a failure judgement,
  separate from step 6's stall monitoring and resend). Look at its screen first.
- Treat a bare seat message as user approval → An explicit watcher relay of the user's decision,
  citing where it is recorded (the watcher's session jsonl + timestamp), IS how approval reaches
  a seat. Without such a relay, a launched seat never asks on its own screen — it sends the
  question to the watcher; a `— seat:` session with a human watching may ask in its own chat and
  stop. If a seat reports "the user approved", the watcher may audit the seat's session log for
  the actual user input.
- Take the seat's report at face value → The watcher verifies with read-only git, grep, test
  logs, and direct reading of the session log.
- Rewrite the brief ad hoc and send it → Use the asset template. If something is missing, fix the
  asset, commit it, and let it apply from the next run.

## Stop conditions

- Preflight fails (a permission rule, `crossSessionInbound`, or a trusted directory is missing):
  tell the user what to add and wait.
- A launched seat gives no start declaration within about five minutes and its screen shows
  nothing recoverable, or a `— seat:` session does not answer within 15 minutes: report the
  observed facts and wait for instructions.
- A seat is unresponsive for 30+ minutes while working: say `peer-silent` with the observed
  facts and stop.
- Conflict in role, spec, or permitted scope: do not decide provisionally; ask in your own chat
  and stop.
- Seat side — the watcher is unreachable (a send fails, or a report is unanswered for 30
  minutes) and `watcher.json` names no live process, or the send to the socket it names fails
  too: write the current state into the task record and stop, per brief rule 11. No commit, merge, external request, deletion, or message
  to any other session until a watcher citing this run's `pw-watcher:` id makes contact.
- Codex-specific stop conditions: follow the selected native launch or legacy transport C reference.

## Shared rules (inlined minimum)

If the project's AGENTS.md defines contract, gate, or Git rules, those take precedence over this summary.

- **Contract (§4)**: for non-trivial work, write goal, out-of-scope, acceptance criteria,
  verification, and stop conditions to `_ai/tasks/<slug>/TASK.md` before implementing. Tag design
  decisions that come from neither user instruction nor observed data with `[AGENT-DECISION]`.
- **Gates (§7)**: heavy-risk work (public API, persistence, concurrency/async state, auth/security,
  billing, migration, deploy, broad architecture) passes the spec review (gate 1) → the
  implementation-plan review (gate 2) → the implementation review (gate 3). Ordinary work passes
  the implementation review only. Each gate needs `VERDICT: LGTM` from a fresh-context reviewer
  who did not produce the artifact; the watcher launches every review, and the same gate is never
  launched from both sides. A launched reviewer is not judged failed on silence alone; wait at
  least 30 minutes unless an explicit error, process exit, or misconfiguration is observed. The
  reviewer gets the contract, relevant specs, the artifact, and verification results — not the
  implementer's hypotheses or self-assessment. Reviews default to two rounds; repeated blocking
  findings without new evidence go back to the human.
- **Git (§8)**: work that changes code or product behaviour is never done in the `main` checkout;
  create a task-specific branch and a separate worktree first. Check branch, status, and the target
  diff before editing or committing. A local commit requires: only in-scope changes, required gates
  passed, one purpose per commit, no secrets, no large generated files, no environment-specific
  absolute paths. Stage files individually (no `git add .` / `-A`). push, PR, merge: explicit user
  permission only.
