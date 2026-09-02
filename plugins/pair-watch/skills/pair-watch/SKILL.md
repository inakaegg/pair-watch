---
name: pair-watch
description: >-
  Use to run two coding-agent chats in parallel (implementer + watcher). The user types
  "/pair-watch:pair-watch <task>" in one chat only; role detection, peer-session discovery, and delivering
  the peer its role brief are automatic. Japanese cues: 「並行体制で」「2チャットで分担」「pairで」.
  The peer chat may start empty. The peer can be a Claude chat or a Codex CLI chat. A Codex peer
  switches transport to file inbox/outbox + rollout audit; when explicitly started from Codex,
  another Codex chat can be the implementer. Not for solo work or in-chat subagent delegation.
metadata:
  language: en
  tested-with: "Claude Code (SendMessage/ListAgents/Monitor), Codex CLI 0.147 file watch and rollout layout ~/.codex/sessions/YYYY/MM/DD/"
---

# Pair-watch — a two-seat setup started from one side

The user opens two chats and types `/pair-watch:pair-watch <one-line task>` in **only one** of them. The
invoked side — unless the invocation is a standby order (step 1) — determines its role, discovers
the peer, delivers the peer's role brief (from `assets/`), and starts the setup. The transport depends on the peer type:

- Peer is a Claude chat: SendMessage, receive-driven (push, token-cheap). No resident polling script.
  Inbound cross-session messages are held for the receiving user's approval by default — even when
  the receiver runs with `--dangerously-skip-permissions` — so replies stall silently until approved,
  and a one-off approval does not carry over to the next message. Before relying on the message
  loop, have the user set `"crossSessionInbound": "accept"` (in `~/.claude/settings.json`, or
  `/config` → "Messages from your other sessions") on both sides.
- Peer is a Codex CLI chat: Codex cannot join SendMessage/ListAgents, so coordination uses agreed
  files (inbox/outbox), completed-message sequences, and rollout audit. The watcher may be Claude,
  or a Codex chat when the setup was explicitly started as Codex + Codex. See
  `references/transport-codex.md` ("transport C").

## Language (read first)

- **Output language**: write everything the user or the peer will read — contracts, inbox/outbox
  entries, declarations, questions, completion reports — in the language of the task description.
  If the task description's language is ambiguous, use the language the user last wrote in.
- **Briefs**: use the templates in `assets/` as they are (English). Do not rewrite them ad hoc.
- **Protocol tokens** (below) are fixed strings. Never translate or paraphrase them, whatever language the task is in.

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
| `{WATCHER_ID} {TASK} {MY_ADDR} {MY_JSONL} {INBOX} {OUTBOX} {WATCH_SCRIPT}` | brief sender | placeholders that must be replaced before sending |

## Procedure

1. **Fix task, role, and peer type** — The task and any role given in the argument take priority.
   State the peer type when the peer is Codex (for example `/pair-watch:pair-watch <task> — peer: Codex CLI`);
   otherwise assume a Claude peer. Without an explicit role, decide in this order: (a) if the peer
   is Codex, you are the watcher; this includes a Codex + Codex setup explicitly started from a
   Codex chat. (b) otherwise decide by your own model: deep-reasoning class → watcher; others →
   implementer. (c) if your model could be read either way, ask the user in one line. A Codex
   watcher is supported only with a Codex implementer; Codex watcher + Claude implementer remains
   unsupported. The watcher never changes code (exceptions: its transport C inbox and creating a
   worktree/branch on the implementer's behalf). If invoked inside Codex without an explicit Codex
   peer, say `codex-invoked` and stop to preserve the Claude-watcher flow. If no task is present
   and this is not a standby invocation, ask the user and stop.
   **Standby invocations do not discover.** If the user's input is a standby order — "wait for
   instructions", "指示待て", "you are the implementer, wait for the pair" — you are the passive
   seat regardless of model class, and a task name in the same line does not cancel the standby —
   it only names the coming work. Run step 2 (locate your own log), state in your own chat that
   you are waiting, and stop there. Do not run step 3's discovery and do not message any session
   — the active side finds you: the user's standby order recorded in your session log is exactly
   what its log scan (step 3b) looks for. From then on follow (a) of step 3: answer the
   identification question when it arrives, then continue with your role's part of step 4
   (normally: receive the brief and reply with the start declaration). Done when: you can state your role, peer type, and task in one line
   (for a standby seat, "waiting to be contacted" is the valid task state).
2. **Locate your own session log** — Claude: build and confirm
   `~/.claude/projects/<slug>/$CLAUDE_CODE_SESSION_ID.jsonl` (each session carries its own id in
   the `CLAUDE_CODE_SESSION_ID` environment variable). Codex: find and confirm the current rollout under
   `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`; record its thread id. Include the path in the
   first peer message. A Codex watcher also uses its path to exclude itself when locating the
   implementer's rollout.
3. **Discover the peer and pin its address** — If the peer is Codex, replace **only the discovery,
   communication, and monitoring means** of steps 3–6 with transport C steps 3C–6C (the rules of
   step 5 — gates, reviewer selection, commit conditions, following your own brief — still apply).
   If the peer is Claude: list peer sessions of the same project with ListAgents, then resolve the
   address in this order. Never broadcast to every session (that interrupts unrelated sessions and
   wastes their tokens), and never send retractions to a session that did not answer — the best
   oracles for "which session is the peer" are the session logs on disk and the user who just
   opened it, not questions fired at the other sessions.
   (a) If an identification question for the same task arrives from a peer before or during your
   own discovery (both chats were invoked), answer it, pin that sender's `from` address, and skip
   the rest — one side discovering is enough. (b) Identify by reading session logs BEFORE
   messaging anyone: list this project's session files (`~/.claude/projects/<slug>/*.jsonl`,
   newest first by mtime, excluding your own) and read the recent user messages of the newest one
   or two. The peer chat is the one whose log matches the setup — a standby line from the user
   ("wait for pair instructions", the task name), or a near-empty session started right around
   the invocation. When one file clearly matches, send the identification question to **that one
   candidate only**: the ListAgents session whose started-time agrees with the file's recent
   activity (if no row can be determined, fall to (c)). The question must state your own role (so
   a same-role conflict surfaces immediately) and say that a non-peer should simply not reply.
   Include the matched jsonl path — the path only, never quoted log content — and tell the peer
   HOW to confirm it: compare against `~/.claude/projects/<slug>/$CLAUDE_CODE_SESSION_ID.jsonl`
   built from its own environment (the peer has not run step 2 yet, so the question must carry
   this method; jsonl filenames do not map to ListAgents names directly, and this confirmation
   closes that gap).
   (c) When candidates are listed but not settled — several equally plausible, a listed
   candidate whose log does not match, or no reply after ~2 minutes — stop probing sessions and
   ask the user in one line which listed session is the peer (show the shortlist); asking the
   user pauses this step until they answer. Then send the same identification question — your
   role stated, as in (b) — to the session they name. At most two sessions total may be
   questioned in one discovery (a cap that also spans any (b) re-runs triggered by (d)), and the
   second slot is reserved for the session the user names — never for a next-best candidate
   picked on your own. When an affirmative reply arrives, copy its `from` attribute verbatim and
   use it as the only address from then on. When no candidate is listed at all, go to (d).
   (d) No candidate at all usually means the user has not opened the peer chat yet. Ask them in
   one line ("did you start the peer chat? open it and I'll find it"), and while waiting watch
   `~/.claude/projects/<slug>/` for a new session file or a fresh update to one other than your
   own — a bounded watch (Monitor or an equivalent loop) for up to 3 minutes from that question
   (the pair is expected to start working right away; if the chat is not up within a few
   minutes, waiting longer will not find it), reading nothing outside this project's session
   directory. When a new or freshly
   updated session appears, identify it via (b); if the user's answer names a session instead,
   that wins. If the watch expires with nothing found, fall to the first stop condition. Done
   when: exactly one peer address is pinned.
4. **Deliver the role brief** — If you are the watcher, read the implementer brief
   (`assets/impl-brief.md` for a Claude peer, `assets/impl-brief-codex.md` for a
   Codex peer); if you are the implementer, read `assets/watch-brief.md`. Fill the
   placeholders and deliver it (Claude: SendMessage; Codex: inbox file). `{WATCHER_ID}`
   is the watcher's own full session id, and the `pw-watcher:` line it fills stays first — that
   line is what binds the seat (see "Seat identity" below). While your own address
   (`{MY_ADDR}`) is unknown, write "reply to the `from` of this message". Done when: the brief is
   delivered and the peer returned a start declaration (implementer) or an acknowledgement (watcher).
5. **Work loop** — From here on, also follow the operating rules of your own role's brief (the asset
   with your role's name); with a Codex peer, transport C takes precedence. Branch/worktree and
   local-commit conditions: see "Shared rules" below. Gates: see "Shared rules" below
   (if your setup has its own review skill or process, it applies on top of that minimum).
   The implementation-review (gate 3) reviewer's first choice is **a different lineage from the
   implementer** (implementer Claude → Codex reviewer; implementer Codex → a fresh-context separate
   Claude process; read-only tools only). When Claude is unavailable, a Codex watcher may launch a
   fresh-context Codex reviewer with read-only tools and only the review artifacts; disclose that
   same-lineage fallback in the result. A review that ended in tool failure or without a `VERDICT`
   line does not count as a round. When idle while waiting for the peer, do not wait indefinitely on
   receive: monitor the peer's session log (Claude: jsonl; Codex: outbox and rollout) for a stall
   (no update for 15 minutes) with Monitor or equivalent, and on a stall send a status check (this
   prevents the deadlock where both sides wait for each other). SendMessage delivery can be lost (a
   successful send does not guarantee receipt): after sending a work instruction, if the peer's
   jsonl shows no activity within a few minutes, resend the same content (this resend is a
   delivery-loss countermeasure, distinct from the 30-minute failure judgement). With a Codex peer,
   instead of resending, check whether the peer started moving after the inbox write, and use
   transport C's user nudge / fallback only when the watch has ended.
6. **Finish** — The watcher verifies the implementer's final report; both sides write a completion
   report in their own chat and dissolve the setup (Codex peer: transport C step 6C). push, PR, and
   merge always require the user's explicit permission.

## Multiple implementer seats (one watcher, N implementers)

The two-seat flow extends to one watcher coordinating several implementer seats when the user
explicitly provides them ("I opened two empty sessions", "use several implementers") or approves
the watcher spawning them ("Watcher-spawned seats" below). This is a supported arrangement, not
an improvisation, with these adjustments:

- **One watcher only.** The watcher stays single and never implements. Every implementer seat is a
  full interactive CLI session — user-opened, or watcher-spawned per "Watcher-spawned seats"
  below; never a subagent (see Wrong shortcut below). Each gets its own identification question
  and its own role brief, labeled (seat A, B, C…).
- **Disjoint scope per seat.** The watcher partitions work so seats never share a branch, worktree,
  or source file. Each brief states the seat's own scope AND the other seats' scopes with the
  files/branches to avoid. Shared files (a ROADMAP, a settings registry) require a one-line
  check-in with the watcher before any seat edits them.
- **One seat, one task — no reuse.** A seat is spawned for one task and retired when that task
  ends. The watcher never hands a finished seat a second, unrelated task, however idle or
  well-briefed it looks: the seat's context already holds the previous task's history, only the
  human could compact it, and the next task starts from a worse position than a fresh session
  (observed live: a reused seat had to be stopped and its work handed over anyway). The rule is
  fixed so the watcher does not weigh it per case — warm build caches and prior familiarity are
  not reasons; the one exception is follow-up work on the *same* task (review fixes, a merge
  conflict on that branch), which stays with its seat. A new task gets a new seat.
- **Gates run per seat.** Each seat's work passes the same gates as in the two-seat flow; the
  watcher launches every reviewer, but reviewers are separate processes and run in parallel, so
  review throughput is not the limit. There is no fixed seat ceiling. What actually bounds N:
  the task graph (seats need disjoint files and branches, so N is at most the number of
  independent tasks ready now), the pile of decisions that need the human (see the trade-offs
  bullet), and the watcher's own context growth. Six seats under a low-effort watcher have been
  planned without strain; add seats as tasks become independent rather than capping by count.
- **The watcher is less busy than it looks.** Observed in live runs: with 4 seats and several
  reviews in flight, the watcher's own work stays light, because it only routes messages, launches
  reviewers, and forwards verdicts — the heavy lifting (implementation, review) runs elsewhere and
  in parallel. Seats were never kept waiting on the watcher; the real watcher-side constraint is
  context growth, not throughput. Do not add a second watcher for load — it splits the audit trail
  and the pending list for no gain.
- **Stall handling scales.** The watcher monitors every seat's session log; nudges are per seat.
  A cross-seat finding (a flake one seat hits in another seat's area) is routed through the
  watcher, never seat-to-seat.
- **Trade-offs to tell the user up front.** Human confirmation cannot keep up with N seats in real
  time: decisions that need the user pile up, so the watcher keeps a single pending list (pushes,
  branch deletions, diff discards, test-expectation changes) and presents it at an agreed
  checkpoint instead of interrupting per item. Watcher context also grows with every seat — long
  runs should compact or checkpoint. Seat context is a budget the agents cannot manage: only the
  human can compact an interactive session — hence the one-seat-one-task rule above.
  The independence guarantee is per pair (watcher ↔ seat); seats are not independent of each
  other's mistakes when their scopes touch.
- **Seat identity: every seat is bound to the watcher that spawned it.** Reusing a seat that
  belongs to another run — or killing one that another watcher still drives — has happened when
  seats were only told apart by generic names (`pw-seat-a`) and idle state. The binding must not
  depend on tmux, because the `script` route has no session name to carry it. Rules:
  - The binding lives in two places that exist on every route. (1) The brief's first line is
    `pw-watcher: <full watcher session id>` — both `assets/impl-brief.md` and
    `assets/impl-brief-codex.md` carry it as their `{WATCHER_ID}` placeholder, so the
    marker reaches the seat on every route without ad-hoc rewriting. It lands in the seat's own
    session jsonl (Codex: rollout file), so the owner of any seat can be found by grepping that
    seat's record for `pw-watcher:`. (2) The watcher writes a registry entry
    `~/.local/state/pair-watch/seats/<watcher-id>/<run-id>/<seat>.json` at spawn: seat label,
    project directory, launch route (tmux session name or pty output file), the seat's session
    id once the handshake returns it, the start timestamp, and — once the seat is retired — a
    `retired` marker with the close timestamp. `<run-id>` is the run's start time
    (ISO-8601, to the second), so a second run from the same watcher chat cannot overwrite the
    entries of seats the first run still owns. The tmux session name carries the run for the same
    reason: `pw-<watcher-id8>-<run-hhmmss>-<letter>`, because `tmux new-session -s` fails on a
    name that already exists, and without the run part a second run collides with a seat the
    first one is still using. The name is a convenience for humans on top of the registry, not
    the source of truth.
  - Before messaging, reusing, or closing any seat, the watcher checks the registry (its own
    `<watcher-id>` directory) and, for anything not in it, the seat's jsonl. Only seats bound to
    its own id are its seats. Seats bound to another id are foreign: never message them, never
    assign them work, never treat them as idle capacity.
  - An unbound seat is not automatically foreign, or the user-opened flow above could never
    start: a chat the user just opened carries no marker until a brief reaches it. Exactly two
    kinds of unbound seat may be claimed — (i) a seat the user named explicitly for this run,
    and (ii) a seat the watcher launched itself and has not yet completed the handshake with.
    Claiming means sending the brief; the binding takes effect the moment its `pw-watcher:`
    line lands. Every other unbound seat (legacy names, sessions the user opened for something
    else) is left alone.
  - Fresh seats by default. A new run spawns new seats; a leftover seat is not capacity, it is
    context already spent. The watcher never closes a foreign seat, however idle it looks — the
    evidence needed to call one abandoned (its pty output file, its checkout) lives in another
    watcher's registry, so the judgement cannot be made from here. List the leftovers to the
    user and leave them running; closing them is the user's call.
  - The watcher retires each of its own seats when that seat's task ends (seat-retirement rule
    below). Retiring does not delete the entry — it marks it `retired` with the close timestamp,
    so the session id stays available for a later `--resume`. The entries are removed together at
    the end of the run, after anything still open is closed, so leftovers do not accumulate for
    the next run.
- **Model and effort of the seats.** The default `opus` at `xhigh` applies to the sessions
  pair-watch launches, i.e. implementer seats. The watcher is the chat the user already started,
  so this procedure cannot set its model or effort: `fable` at `low` is a recommendation for
  which chat to run pair-watch from, not a value the skill applies. The user's explicit words in
  the invocation override the launch defaults (`/pair-watch:pair-watch <task> — implementer:
  opus(xhigh)`). Pair-watch reads no other tool's configuration for this. In its first reply the
  watcher states the model and effort it will launch seats with, and the model it is itself
  running as; if that does not match what the user asked of the watcher, it says so and asks
  whether to restart pair-watch from a different chat — before the first spawn.
- **Watcher-spawned seats (verified on macOS).** Seats do not have to be user-opened: with the
  user's explicit go-ahead for that run, the watcher can launch a seat itself as a real CLI
  session, choosing model and reasoning effort freely (`claude --model ... --effort ...`) — this
  sidesteps the subagent limitation where effort is inherited from the parent and cannot be
  raised. A pty is required; two verified launch routes:
  - tmux: `tmux new-session -d -s <seat> -c <trusted-project-dir> 'claude --model ... --effort ... --dangerously-skip-permissions "<brief>"'`
  - no tmux (macOS/BSD): `script -q /dev/null claude ... "<brief>" < /dev/null` as a background
    process (Linux syntax: `script -qc "claude ..." /dev/null`).
  Rules learned the hard way (verified in live runs unless noted):
  - **Add spawn permissions BEFORE the first spawn** — without them the launch can fail.
    Observed live in a watcher session running in auto permission mode: the harness's
    permission classifier blocked `claude --dangerously-skip-permissions` spawns (tmux route:
    denied outright on every attempt; script route: intermittently escalated to a user
    prompt, intermittently denied). Chat-level user approval did not override the classifier,
    and the watcher cannot add the rules itself (self-editing `settings.json` permissions was
    also blocked — by design). So the brief to the USER, before the first spawn: add
    `"Bash(tmux new-session:*)", "Bash(tmux send-keys:*)", "Bash(tmux capture-pane:*)",
    "Bash(tmux kill-session:*)", "Bash(tmux ls:*)"` to `permissions.allow` — preferably in the
    PROJECT's `.claude/settings.json` (scoped to that repo), or in `~/.claude/settings.json`
    if seats are spawned across many projects. Note the trade-off before the user chooses:
    these rules let any session in their scope start arbitrary commands via
    `tmux new-session`, inject keys, and read panes without prompting, so a global entry
    widens the boundary well beyond pair-watch — recommend project-local, and removal when
    the seat workflow is no longer used. In the observed environment (no conflicting
    deny/ask rules or hooks), the allowlisted tmux launch then ran without any prompt;
    an allow rule cannot override deny/ask rules or blocking hooks — those take precedence,
    so a launch can still be stopped where they match. Keep
    the env scrub INSIDE the string passed to tmux so the outer command still starts with
    `tmux` and matches the rule. A compound command (`pkill ...; tmux ...`) does not match —
    run the tmux call as its own Bash invocation.
  - **In an IDE-hosted watcher, prefer tmux over script for UX too**: a `script`-route seat
    spawned from a VSCode-hosted session surfaces as a visible terminal in the user's IDE
    (observed live; confusing — the user sees a terminal open "by itself"). A detached tmux
    session stays invisible. Combined with the input asymmetry below, tmux is the default
    route whenever available; use `script` only when tmux is absent.
  - **Scrub the inherited env** before launching: unset `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`,
    `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_MESSAGING_SOCKET`, `CLAUDE_CODE_MESSAGING_TOKEN`,
    `CLAUDE_CODE_SSE_PORT`, `CLAUDE_CODE_ENTRYPOINT` and the other `CLAUDE*` vars the watcher's
    own harness set. With them inherited, the seat registers as a child/remote session and its
    messaging misbehaves.
  - **Never pass `--disallowedTools AskUserQuestion`**: observed to remove SendMessage from the
    seat as well, leaving it unable to reply at all. Question discipline comes from the brief,
    not from tool removal.
  - **Launch in a trusted project directory**: in an untrusted cwd the seat stalls invisibly at
    the workspace-trust dialog before the prompt is even read. Trust is per directory and
    persists in the CLI config once accepted — except for git linked worktrees, where an
    acceptance was observed not to persist, so the dialog can return on the next spawn. For a
    seat that must work in a worktree, the verified route is cwd = the trusted main checkout
    plus `--add-dir <worktree>` (no dialog, and the seat can write in the added directory).
    Beware: `--add-dir` takes multiple values, so a positional prompt placed after it is
    swallowed as a path — put the prompt before the flag, or send instructions after startup.
    As a last resort a dialog can be cleared from outside via `tmux send-keys` (verified).
  - **Confirm `crossSessionInbound: accept` is set before spawning**: a spawned seat has no human
    to approve inbound messages, so without it the startup handshake goes silent — a symptom
    indistinguishable from the trust-dialog stall. "Both sides" means every seat in an N-seat run.
  - **The brief must route questions to the watcher**: tell the seat "no human watches this
    screen; anything that needs a decision goes via SendMessage to the watcher, never into your
    own chat". The watcher answers from the task contract or puts the item on the pending list in
    its own (visible) chat — the user keeps watching one chat, regardless of seat count.
  - **Monitor event-driven, not by polling.** The watcher acts only on signals: the startup
    handshake (seat must appear in ListAgents and answer an identification message within a
    deadline — if not, look at its screen: `tmux capture-pane` for tmux seats, the pty output
    file for script seats; this is how a trust dialog blocking startup was caught) and incoming
    replies. A seat whose brief obliges it to report needs no idle subscription — observed in
    live runs, `notify_when_idle` notices only duplicated the reports and added noise; when a
    report is overdue, stat the seat's session jsonl mtime instead. Attach `notify_when_idle`
    (a one-shot subscription, consumed by the next idle) only to a seat that has no reporting
    duty on its current instruction.
  - **A seat stuck on an on-screen chooser (AskUserQuestion, a dialog) cannot be messaged out of
    it** — queued messages are only read at the seat's next tool round, and a seat waiting for
    key input never reaches one. Recovery differs by route: a tmux seat accepts injected keys
    (`tmux send-keys` — Esc to dismiss, arrows+Enter to choose; verified live by clearing a
    workspace-trust dialog with Down+Enter), a script seat accepts no outside input, so the recovery is kill +
    `claude --resume <session-id>` in a fresh pty. This asymmetry is why tmux is the preferred
    route when available. A seat that instead *asks in text* and goes idle is the easy case:
    the idle notice fires and a SendMessage answer resumes it.
  - Spawned seats run with `--dangerously-skip-permissions`, so spawning is per-run user opt-in.
    Cleanup follows the seat-retirement rule in the "Seat cleanup" bullet below.
- **Seat cleanup depends on where the sessions run.** Sessions are ordinary processes: in a
  terminal a finished seat can be killed, and its tab closed too, from the watcher's shell.
  Verified flow on macOS Terminal.app: SIGTERM the seat's `claude` process, then SIGHUP its parent
  shell — with the profile setting "close the tab when the shell exits" the tab closes by itself
  (observed to work even with the "exited cleanly" variant, despite the signal death). This is
  plain process signalling: no AppleScript, no automation-permission dialog. Driving the tab via
  AppleScript + Cmd+W also works, but it needs a one-time automation grant and sends the keystroke
  to the frontmost window (racy if the user is clicking around) — prefer the signal route. Under
  tmux the portable equivalent is `tmux kill-session`. `claude --resume <session-id>` brings a
  killed seat back with context if needed — so a use-once-and-retire seat pool is fully
  manageable. In an IDE (VSCode), killing the process ends the session but the tab stays; there
  is no API to close tabs from outside, so a large seat pool accumulates dead tabs the user must
  close by hand. Prefer terminal/tmux for many-seat runs, or keep the pool small in an IDE.
  **Retiring a seat** (kill without return, including the tab-closing flow above): a
  watcher-spawned seat is retired by the watcher when its task ends — after the seat's final
  report, with its branch committed or its uncommitted state handed over in the task's `_ai/`
  record, and never while it still holds unreported work. Nothing is lost by the kill: the seat's
  session log stays on disk and `claude --resume <session-id>` brings the conversation back with
  its context when someone later needs to ask that seat something — which is why the registry
  entry is marked `retired` rather than deleted at the kill, and keeps the session id until the
  run ends. Leaving finished seats running instead costs memory per process and clutters
  the session list once a run reaches tens of seats. A user-opened seat is retired only on the
  user's word. Stall recovery of a spawned seat (kill + `claude --resume <session-id>` of a seat
  stuck on an on-screen chooser) is likewise the watcher's call, reported to the user afterwards.

## Pair-watch or the Workflow tool?

Both run several agents at once; they differ in what the agents are.

- **Pair-watch seats are interactive sessions.** Each seat can be messaged mid-task, nudged when
  its log stalls, given a changed brief, or opened by the user to look at. Each seat carries its
  own model and effort (`claude --model … --effort …`). Reviewers are separate processes, so a
  different-lineage reviewer (Codex) is a first-class choice. Use pair-watch when the work is
  long, the user may add or redirect tasks while it runs, or a seat must hold uncommitted state
  across several instructions.
- **Workflow agents are subagents driven by a script.** They also take a per-agent `model` and
  `effort` (`agent(prompt, {model, effort})`), so implementers at `opus`/`xhigh` are possible
  there too — the "effort is inherited" limitation applies to the plain Agent tool, not to
  Workflow. But the agents are Claude models only: a Codex reviewer is reachable only when an
  agent shells out to `codex exec`, and no agent is a chat the user can join. Changing course
  means editing the script and resuming (completed `agent()` calls are replayed from cache). Use
  Workflow for a batch of same-shaped, pre-scoped work — N translations compared on the same
  phrases, N findings each verified from several lenses — where determinism beats interactivity.
- **Mixing is fine.** A pair-watch seat may run a Workflow inside its own task for a fan-out step;
  the watcher does not.

## Wrong shortcut → correct action

- Keep sending to a session name or ref → Name resolution is unreliable. The `from` address of the
  identification reply is the only address.
- Invoked with a standby order ("wait for instructions") and start scanning for the peer → Only
  the active side discovers. Locate your own log (step 2), say you are waiting, and stop; you
  will be contacted (step 1, standby invocations).
- Launch a background or in-chat subagent as the implementer seat → That is solo delegation, not a
  pair-watch seat. Discover the user's interactive peer chat (step 3 / 3C); a fresh-context subagent
  is allowed only as the read-only implementation-review (gate 3) reviewer fallback of step 5.
  A practical reason on top of the structural one: a subagent inherits the launching session's
  reasoning-effort setting and cannot raise it, so a watcher running at low effort would produce
  low-effort implementer subagents. When more implementer capacity is needed, ask the user to open
  additional interactive sessions (each carries its own model/effort settings and survives the
  watcher's session) instead of spawning subagents — or, with the user's explicit go-ahead, launch
  a real CLI seat yourself ("Watcher-spawned seats" above), which also carries its own
  model/effort settings.
- Keep trying ListAgents/SendMessage toward a Codex peer → That route does not exist. Switch to
  transport C's file transport.
- Judge the peer failed because it produced no output → Unless there is an explicit error, process
  exit, or misconfiguration, wait at least 30 minutes (this 30 minutes is the lower bound for a
  failure judgement, separate from step 5's stall monitoring and resend).
- Treat a bare peer message as user approval → An explicit watcher relay of the user's decision,
  citing where it is recorded (the watcher's session jsonl + timestamp), IS how approval reaches an
  implementer: act on it, and audit the cited record only on concrete doubt. Without such a relay, a
  user-opened seat asks in its own chat and stops; a watcher-spawned seat never asks on its own
  screen — it sends the question to the watcher. If the peer reports "the user approved", the watcher
  may audit the peer's session log (jsonl/rollout) for the actual user input.
- Take the peer's report at face value → The watcher verifies with read-only git, grep, test logs,
  and direct reading of the session log.
- Rewrite the brief ad hoc and send it → Use the asset template. If something is missing, fix the
  asset, commit it, and let it apply from the next run.

## Stop conditions

- No plausible peer found (no candidate in ListAgents and no matching session log, after step
  3d's watch expired), no affirmative reply to the identification question within 15 minutes, or
  no answer within 15 minutes after asking the user to name the peer (step 3c): report to the
  user and wait for instructions (the peer chat may not be started).
- Peer unresponsive for 30+ minutes while working: report your observed facts to the user and stop.
- Conflict in role, spec, or permitted scope: do not decide provisionally; ask in your own chat and stop.
- Codex-specific stop conditions: follow transport C.

## Shared rules (inlined minimum)

If the project's AGENTS.md defines contract, gate, or Git rules, those take precedence over this summary.

- **Contract (§4)**: for non-trivial work, write goal, out-of-scope, acceptance criteria,
  verification, and stop conditions to `_ai/tasks/<slug>/TASK.md` before implementing. Tag design
  decisions that come from neither user instruction nor observed data with `[AGENT-DECISION]`.
- **Gates (§7)**: heavy-risk work (public API, persistence, concurrency/async state, auth/security,
  billing, migration, deploy, broad architecture) passes the spec review (gate 1) → the
  implementation-plan review (gate 2) → the implementation review (gate 3). Ordinary work passes
  the implementation review only. Each gate needs `VERDICT: LGTM` from a
  fresh-context reviewer who did not produce the artifact; in a two-agent setup the side that did
  not produce the artifact launches and runs the review, and the same gate is never launched from
  both sides. A launched reviewer is not judged failed on silence alone; wait at least 30 minutes
  unless an explicit error, process exit, or misconfiguration is observed. The reviewer gets the
  contract, relevant specs, the artifact, and verification results — not the implementer's
  hypotheses or self-assessment. Reviews default to two rounds; repeated blocking findings without
  new evidence go back to the human.
- **Git (§8)**: work that changes code or product behaviour is never done in the `main` checkout;
  create a task-specific branch and a separate worktree first. Check branch, status, and the target
  diff before editing or committing. A local commit requires: only in-scope changes, required gates
  passed, one purpose per commit, no secrets, no large generated files, no environment-specific
  absolute paths. Stage files individually (no `git add .` / `-A`). push, PR, merge: explicit user
  permission only.
