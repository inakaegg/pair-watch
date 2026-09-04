# User-facing strings (en)

Strings the skill says to the user. Keep the meaning stable when editing; the protocol tokens in SKILL.md are never translated.

- ask-task: "No task found in the argument or the conversation. What is the task (one line)?"
- spawn-permissions: "Before I can launch a seat, add these to permissions.allow (preferably in this project's .claude/settings.json): \"Bash(tmux new-session:*)\", \"Bash(tmux send-keys:*)\", \"Bash(tmux capture-pane:*)\", \"Bash(tmux kill-session:*)\", \"Bash(tmux ls:*)\". Within their scope these rules let any session start commands via tmux, inject keys, and read panes without prompting — broader than pair-watch; remove them when you stop using launched seats. Also confirm \"crossSessionInbound\": \"accept\" in ~/.claude/settings.json, or the seat's replies will be held for approval. Tell me when done."
- seat-not-found: "No session named {SEAT} is listed. Is that chat open? Give me the exact name from its session list, or drop \"— seat:\" and I will launch a seat instead."
- seat-silent: "Seat {SEAT} has not sent its start declaration. Its screen shows: {SCREEN}. I will {ACTION}."
- codex-invoked: "This Codex chat has no explicit Codex peer. A Codex chat cannot launch or message Claude sessions, so start pair-watch from a Claude chat, or name a Codex implementer with \"— peer: Codex CLI\" to run Codex + Codex."
- codex-first-paste: "Please paste into the Codex chat: \"Read {INBOX} and follow it.\""
- codex-nudge: "The Codex implementer's watch has ended. Please type in the Codex chat: \"check the inbox\"."
- codex-watcher-nudge: "The Codex watcher's watch has ended. Please type in the watcher chat: \"check the outbox\"."
- peer-silent: "Seat {SEAT} has been unresponsive for over 30 minutes. Observed facts: {FACTS}. Stopping here."
