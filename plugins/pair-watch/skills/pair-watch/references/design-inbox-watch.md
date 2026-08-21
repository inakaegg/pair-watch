# Design note — inbox-watch for a Codex implementer, and the alternatives not taken

Summary:

- "Transport C" is pair-watch's communication mode when the peer is Codex (C for Codex;
  concretely, the inbox/outbox file exchange defined in `transport-codex.md`).
- Codex only runs while the user is talking to it (turn-driven). So in the first version of
  transport C, every time the watcher wrote an instruction, the user had to type
  "check the inbox" into the Codex chat by hand.
- The fix: while waiting for a reply, the implementer no longer ends its turn. It keeps watching
  the inbox for updates with a shell sleep loop (inbox-watch): one watch is about 5 minutes,
  re-armed up to 6 times. If no instruction arrives by then, it ends the turn, and from that point
  the user nudges Codex as before.
- Waiting itself consumes zero tokens. Tokens are spent only for the instant the watch is re-armed
  every ~5 minutes, and the number of re-arms is capped.
- A watch on/off setting, a return to the original always-read-the-transcript mode, and periodic
  wake-ups via cron were each considered and rejected. The reverse pattern (Codex as watcher) and
  Codex-with-Codex setups are "not supported" by design. Reasons below.
- In one sentence: this change cheaply restores for Codex peers the property the original pair
  had — the moment the peer writes, the other side starts moving.

The rest is the detailed reasoning. Read it when revising the skill itself; agents do not need it
at run time.

## History

1. **First generation (reading each other's transcripts)** — Early pair had both sides, Claude and
   Codex alike, periodically read the peer's chat transcript file (Claude: the session jsonl;
   Codex: the rollout) and react to it. The moment the peer wrote something, the other side would
   move — but token consumption was high, because each side kept reading transcript content.
2. **Moving to SendMessage (Claude with Claude)** — Claude Code later shipped cross-session
   messaging (SendMessage/ListAgents), and Claude-with-Claude became push-driven: wake me when
   something arrives. The continuous reading disappeared and token consumption dropped sharply.
3. **Transport C, first version (Codex peer)** — Codex cannot join the SendMessage mechanism, so a
   Codex-only transport was added: agreed files (inbox/outbox) plus rollout audit. This is
   transport C. But its only way of getting Codex moving was "the user types one line into the
   Codex chat", which lost the automatic reactivity the first generation had.
4. **inbox-watch (this design)** — Restores that reactivity, not by going back to transcript
   reading, but by watching a file for updates without ending the turn.

## Problem

Codex CLI is turn-driven: once a turn ends, nothing happens until the user speaks to it again. In
the first version of transport C, a manual user step was required at every gate verdict, every
finding handoff, and every docs handoff — tedious enough to defeat the point of a two-seat setup.

## The design taken: watch without ending the turn (inbox-watch)

After writing its report to the watcher, the implementer does not end the turn. It runs a shell
sleep loop that checks the inbox file's modification time. One watch lasts about 5 minutes; if
there was no update it re-arms, and after about 30 minutes in total it gives up and ends the turn.
After that, as before, the user nudges the Codex chat with one line.

The rationale is the token cost breakdown:

- While sleep blocks, the model is processing nothing. The waiting itself costs zero.
- Tokens are spent only at the instant control returns to the model after each sleep: a small
  "no update → watch again" step every ~5 minutes. The conversation context is served from cache,
  so the real cost per re-arm is small.
- Re-arms stop after 6 attempts, so the cost is bounded even when no reply ever comes.

So one wait costs at most "a small step, six times" — cheap as the price of removing a manual
user action from every exchange.

## Alternatives not taken

### A watch on/off setting

Not taken, because the "off" behaviour happens automatically rather than by configuration. In an
environment where the watch command needs approval on every run, or gets killed by a timeout, the
implementer writes that fact to the outbox, ends the turn, and the setup falls back to the manual
nudge flow. Whether an environment "should be off" is discovered at run time; the user has nothing
to choose in advance. A setting would add a question to every start and fork the instructions,
buying nothing.

### Going back to reading each other's transcripts

Not taken, for two reasons.

1. On the watcher (Claude) side, "keep watching" is already effectively free through
   wake-on-change mechanisms (Monitor and the like). The only difference from the first generation
   is reading the transcript continuously versus reading the essentials when something changed —
   and continuous reading pays extra tokens for the same information.
2. The cases that genuinely require reading a whole transcript — verifying a start declaration,
   checking the reasoning before a gate, a report contradicting the artifacts — are handled as
   per-occasion audits by design. Constant surveillance would not catch more problems.

### Waking Codex periodically with cron or similar

Not taken. An external periodic wake-up runs inference that re-reads the whole conversation on
every wake, which costs more than re-arming a sleep loop. The current design, which moves on a
file update, is sufficient.

### Codex as watcher (the reverse pattern), and Codex with Codex

Not supported, as a design decision. The essence of the watcher role is receive-driven reaction to
irregular events — the peer's reports, stalls, and review requests. Codex cannot join
SendMessage/Monitor and cannot act on its own outside a turn. inbox-watch is a way to keep "the
implementer waiting for a reply" cheap; a watcher that must keep reacting to events cannot be
built on a turn-driven runtime. The watching would degrade into "the user wakes Codex every time",
which destroys the automation the setup exists for. In addition, the author's shared agent rules
want a deep-reasoning model for gate stewardship and audit, so the watcher is fixed to Claude. The
same points are stated in the assumptions and constraints of `transport-codex.md`.

## Future improvement candidates

- Lengthen a single watch. Once the implementer's environment is confirmed to allow long command
  runtimes, changing 5 min × 6 to 10 min × 3 halves the number of token-consuming re-arms. This
  goes in as a better default, not as a setting.

## Constraints (accepted knowingly)

- The watch ends with the turn. After the ~30-minute cap, or after the implementer reaches a stop
  condition, one line from the user is needed again.
- Only the modification time is watched, so there is no way to signal anything without writing to
  the inbox. This is also a virtue: every exchange lands in a file and can be audited later.
- The watch cannot work in environments that require approval for every command. No
  approval-bypass mechanism will be built; the setup switches to manual operation instead.
