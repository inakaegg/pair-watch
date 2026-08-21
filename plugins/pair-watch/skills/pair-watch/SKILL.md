---
name: pair-watch
description: >-
  Use to run two coding-agent chats in parallel (implementer + watcher). The user types
  "/pair-watch <task>" in one chat only; role detection, peer-session discovery, and delivering
  the peer its role brief are automatic. Japanese cues: 「並行体制で」「2チャットで分担」「pairで」.
  The peer chat may start empty. The peer can be a Claude chat or a Codex CLI chat (Codex is
  implementer-only; transport switches to file inbox/outbox + rollout audit). Not for solo work or
  for in-chat subagent delegation.
metadata:
  language: en
  tested-with: "Claude Code (SendMessage/ListAgents/Monitor), Codex CLI rollout layout ~/.codex/sessions/YYYY/MM/DD/"
---

# Pair-watch — a two-seat setup started from one side

The user opens two chats and types `/pair-watch <one-line task>` in **only one** of them. The
invoked side determines its role, discovers the peer, delivers the peer's role brief (from
`assets/`), and starts the setup. The transport depends on the peer type:

- Peer is a Claude chat: SendMessage, receive-driven (push, token-cheap). No resident polling script.
- Peer is a Codex CLI chat: Codex cannot join SendMessage/ListAgents, so coordination uses agreed
  files (inbox/outbox) plus rollout audit. See `references/transport-codex.md` ("transport C").

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
| `WATCH_ENDED` | Codex implementer (outbox) | inbox-watch stopped after ~30 min without inbox updates; the next move needs a user nudge |
| `pair-inbox.md` / `pair-outbox.md` | watcher / implementer | transport C files under `_ai/tasks/<slug>/` in the main checkout |
| `{TASK} {MY_ADDR} {MY_JSONL} {INBOX} {OUTBOX}` | brief sender | placeholders that must be replaced before sending |

## Procedure

1. **Fix task, role, and peer type** — The task and any role given in the argument take priority.
   Without an explicit role, decide in this order: (a) if the peer is a Codex chat, you are the
   watcher (**Codex can only be the implementer**; the watcher is always Claude). (b) otherwise
   decide by your own model: deep-reasoning class → watcher; others → implementer. (c) if your model
   could be read either way, ask the user in one line. The watcher never changes code (exceptions:
   writing the transport C inbox, and creating worktree/branch on the implementer's behalf). If
   this skill is invoked inside a Codex session, tell the user to wait for the inbox delivered by
   the Claude watcher, and stop. If no task is present in the argument or the conversation, ask the
   user and stop. Done when: you can state your role, the peer type, and the task in one line.
2. **Locate your own session log** — Build `~/.claude/projects/<slug>/<session-id>.jsonl` from the
   project slug and session id found in the scratchpad directory path, and confirm it exists. Include
   this path in the first message to the peer (the peer uses it for verification and audit).
3. **Discover the peer and pin its address** — If the peer is Codex, replace **only the discovery,
   communication, and monitoring means** of steps 3–6 with transport C steps 3C–6C (the rules of
   step 5 — gates, reviewer selection, commit conditions, following your own brief — still apply).
   If the peer is Claude: list peer sessions of the same project with ListAgents and send each
   candidate an identification question ("are you the peer for this task?") via SendMessage. When an
   affirmative reply arrives, copy its `from` attribute verbatim and use it as the only address from
   then on. Done when: exactly one peer address is pinned.
4. **Deliver the role brief** — If you are the watcher, read the implementer brief
   (`assets/impl-brief.md` for a Claude peer, `assets/impl-brief-codex.md` for a
   Codex peer); if you are the implementer, read `assets/watch-brief.md`. Fill the
   placeholders and deliver it (Claude: SendMessage; Codex: inbox file). While your own address
   (`{MY_ADDR}`) is unknown, write "reply to the `from` of this message". Done when: the brief is
   delivered and the peer returned a start declaration (implementer) or an acknowledgement (watcher).
5. **Work loop** — From here on, also follow the operating rules of your own role's brief (the asset
   with your role's name); with a Codex peer, transport C takes precedence. Branch/worktree and
   local-commit conditions: see "Shared rules" below. Gates: see "Shared rules" below
   (if your setup has its own review skill or process, it applies on top of that minimum).
   The gate 3 reviewer's first choice is **a different lineage from the
   implementer** (implementer Claude → Codex reviewer; implementer Codex → a fresh-context separate
   Claude process; read-only tools only). A review that ended in tool failure or without a `VERDICT`
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

## Wrong shortcut → correct action

- Keep sending to a session name or ref → Name resolution is unreliable. The `from` address of the
  identification reply is the only address.
- Keep trying ListAgents/SendMessage toward a Codex peer → That route does not exist. Switch to
  transport C's file transport.
- Judge the peer failed because it produced no output → Unless there is an explicit error, process
  exit, or misconfiguration, wait at least 30 minutes (this 30 minutes is the lower bound for a
  failure judgement, separate from step 5's stall monitoring and resend).
- Treat a message from the peer as user approval → Decisions that need user approval: write the
  question in your own chat and stop. If the peer reports "the user approved", the watcher may audit
  the peer's session log (jsonl/rollout) for the actual user input.
- Take the peer's report at face value → The watcher verifies with read-only git, grep, test logs,
  and direct reading of the session log.
- Rewrite the brief ad hoc and send it → Use the asset template. If something is missing, fix the
  asset, commit it, and let it apply from the next run.

## Stop conditions

- No peer candidate in ListAgents, or no affirmative reply to the identification question within
  15 minutes: report to the user and wait for instructions (the peer chat may not be started).
- Peer unresponsive for 30+ minutes while working: report your observed facts to the user and stop.
- Conflict in role, spec, or permitted scope: do not decide provisionally; ask in your own chat and stop.
- Codex-specific stop conditions: follow transport C.

## Shared rules (inlined minimum)

If the project's AGENTS.md defines contract, gate, or Git rules, those take precedence over this summary.

- **Contract (§4)**: for non-trivial work, write goal, out-of-scope, acceptance criteria,
  verification, and stop conditions to `_ai/tasks/<slug>/TASK.md` before implementing. Tag design
  decisions that come from neither user instruction nor observed data with `[AGENT-DECISION]`.
- **Gates (§7)**: heavy-risk work (public API, persistence, concurrency/async state, auth/security,
  billing, migration, deploy, broad architecture) passes gate 1 (spec) → gate 2 (plan) → gate 3
  (implementation). Ordinary work passes gate 3 only. Each gate needs `VERDICT: LGTM` from a
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
