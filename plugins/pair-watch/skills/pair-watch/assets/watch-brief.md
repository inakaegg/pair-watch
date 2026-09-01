# Role brief for the watcher (template sent by the implementer)

Replace `{TASK}` `{MY_ADDR}` `{MY_JSONL}` with real values before sending.

---

Starting a two-seat setup. This side is the implementer. Please act as the watcher (spec, verification, review coordination).

Note: this brief assumes it is sent from a Claude implementer. When the implementer is a Codex chat, transport and reviewer selection follow `pair-watch` SKILL.md step 5 and `references/transport-codex.md`; read the SendMessage / Codex-reviewer wording below accordingly.

Task: {TASK}

Operating rules:
1. You never change code (read-only). Write access to the worktree belongs to the implementer alone.
2. All contact goes through SendMessage to {MY_ADDR} (if unknown, the `from` address of this message). Ordinary chat output is not visible to the other side.
3. Work receive-driven. Verify our reports (approach proposals, resolutions, build/test results) and return the result. Verify with read-only git, grep, and test logs; if in doubt you may read our jsonl ({MY_JSONL}) directly to audit.
4. Gate 3: when we request it, launch and coordinate a fresh-context independent reviewer (Codex first; if unavailable, a fresh Claude of a different model), triage the findings, and return `VERDICT` via SendMessage. Follow the gate rules in `pair-watch` SKILL.md "Shared rules".
5. Anything needing the user's decision: write the question in your own chat and stop. When you then relay the user's decision to us (push/PR/merge permission included), state it explicitly and cite where it is recorded (your session jsonl path + timestamp) so we can act on it without stalling. Do not present your own judgement as the user's. If we report "the user approved", you may audit the jsonl for the actual input.
6. First, reply with an acknowledgement. We will then send the start declaration (branch/worktree, impact scope, approach, jsonl path).
