# ROADMAP

Implementation order and progress. Implementation status is recorded only in this file.

## Instructed by the author, not yet implemented

Author instructions and requests not yet implemented, with dates. When done, move the entry to "Current state" and delete the row.

- [2026-08-29] Multi-seat arrangements beyond one watcher + N implementers (e.g. planner + implementer + reviewer). Survey seat combinations in other libraries and skills (BMad workflows etc.) and design which combinations this skill formally supports before documenting them. The observation notes from the first live run are in `_ai/notes/2026-08-29-multi-seat-draft.md` (file-ownership partitioning, serialized merges, centralized operations, an instruction ledger) — **not started**. Note: the basic one-watcher + N-implementers arrangement was documented ahead of this design on 2026-08-31 by explicit author instruction (see "Current state"); this entry now covers only the remaining combinations.


## Current state

- 2026-09-05: Version 0.5.0 adds native Codex tmux launch, token-bound thread identity, queue notifications, separate seat channels, and owned retirement. Two real 0.153.4 seats completed start/bind/notify/final-report/stop; mid-turn delivery was separately verified. Model and effort defaults and fallback order live in settings files. Both plugin manifests and SessionStart hook paths have deterministic validation; kit Bash and apply_patch hooks ran live. The full installed-plugin natural-language task remains unverified.

- 2026-09-05: pair-watch is also installable as a Codex plugin (`.codex-plugin/plugin.json` next to the Claude manifest, `.agents/plugins/marketplace.json` at the repository root). Same skill body, same version; `scripts/check-protocol.sh` keeps the two manifests' name and version equal. Installed and listed locally with `codex plugin marketplace add` / `codex plugin add` on codex-cli 0.151; no live Codex + Codex run through the installed plugin yet.
- 2026-09-04: Watcher-launched seats are the default (0.4.0). The invoked chat is always the watcher; it launches implementer seats under tmux and no longer searches for a peer. Peer discovery (ListAgents matching, session-log scanning, the identification question), standby invocations, and role detection by model class were removed; a user-opened chat is used only when named with `— seat: <name>`. Launch mechanics moved to `references/seat-launch.md`. Launching a Codex seat from the watcher remains unverified, so Codex seats are still started by the user. Documented by author instruction after a live run in which discovery failed (the peer's session file did not exist yet) and a watcher-launched seat worked end to end.
- 2026-09-01: Watcher-spawned seats are documented in the skill (launch under tmux or script(1) with env scrubbing, question routing to the watcher, stall detection and kill + `--resume` recovery) together with seat cleanup by plain signals (SIGTERM the seat, SIGHUP its shell; verified on macOS Terminal.app) and the `crossSessionInbound: accept` requirement for unattended message delivery. Verified live and documented by author instruction.
- 2026-08-31: The one-watcher + N-implementer-seats arrangement is documented in the skill ("Multiple implementer seats" section) and in both READMEs, including its trade-offs (user confirmation backlog, watcher context growth, review throughput ceiling, seat context that only the human can compact). Documented by author instruction during the second live run (1 watcher + up to 4 seats).
- 2026-08-31: Recorded why implementer seats must be real sessions, not subagents (subagents inherit the launching session's reasoning effort).
- 2026-08-29: Standby invocations wait without discovering (the active side finds them).
