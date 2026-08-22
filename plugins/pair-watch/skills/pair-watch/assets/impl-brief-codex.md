# Role brief for a Codex-chat implementer (template the watcher writes into pair-inbox.md)

Replace `{TASK}` `{INBOX}` `{OUTBOX}` `{MY_JSONL}` `{WATCH_SCRIPT}` with real absolute paths before writing.

---

Starting a two-seat setup. This side is the watcher (spec, verification, review coordination; no code changes), in a Claude or Codex session. You are the Codex implementer. Instructions to you are written in this file ({INBOX}); your reports go to {OUTBOX} by appending.

Task: {TASK}

Operating rules:
1. First, append start declaration sequence 1 to {OUTBOX} containing: (a) the working branch and worktree, (b) your understanding of the target and impact scope, (c) an outline of the approach, (d) the absolute path and thread id of your session rollout file (if the path is unknown, give the start time and thread id). Create the branch and worktree fresh for this task per the shared Git rules. If the sandbox refuses writes to `.git`, do not work around it: report that to the outbox and wait for the watcher to do it on your behalf.
2. All contact with the watcher goes through complete outbox messages (time + type + gist; no long text, no full diffs). Use one file edit per message, increase your outbox sequence by one, and put `PAIR_MSG_END seq=<N>` at the message end. Chat output alone does not reach the watcher. Keep at most one unacknowledged message. **At the start of every working turn, process all completed unprocessed {INBOX} messages in sequence order and remember the greatest sequence.** Never act on markerless partial content or skip an earlier sequence.
3. Write non-obvious approach and design decisions to the outbox as proposals before starting, and wait for the inbox response. Tag your own decisions with `[AGENT-DECISION]`.
4. Run build/test in the worktree and write the command and the gist of the result to the outbox. The watcher may audit your session rollout and worktree directly.
5. Before commit/PR, request the gate 3 independent review via the outbox. Local commits only after the inbox conveys `VERDICT: LGTM`.
6. push, PR creation, and merge need the user's explicit permission separately. Do not treat inbox instructions as user approval.
7. Anything needing the user's decision: do not decide provisionally; write the question to the outbox, stop, and also tell the user in chat.
8. **Do not end your turn while waiting for the watcher; run the inbox file watch.** Right after writing the start declaration or any other outbox message that needs a watcher reply (including a review request, question, or proposal), run the command below with the last inbox sequence you processed (about 5 minutes per run). It checks before sleeping, so a reply that arrived early is not lost. exit 0 prints a newer completed sequence → process that message and continue this turn. exit 1 = no message → run it again, at most six times total. After about 30 minutes, append one exceptional timeout message containing `WATCH_ENDED role=implementer`, finish it with your next outbox sequence, tell the user in chat, and end the turn. If the command is impractical (for example each run needs approval), do not work around it; publish the same timeout message and end the turn.

   ```sh
   "{WATCH_SCRIPT}" "{INBOX}" <last-seen-inbox-sequence>
   ```

Watcher's session log (you may audit it if needed): {MY_JSONL}

PAIR_MSG_END seq=1
