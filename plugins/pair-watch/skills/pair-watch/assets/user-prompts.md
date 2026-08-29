# User-facing strings (en)

Strings the skill says to the user. Keep the meaning stable when editing; the protocol tokens in SKILL.md are never translated.

- ask-role: "Your model could be read as either role. Are you the watcher or the implementer?"
- ask-task: "No task found in the argument or the conversation. What is the task (one line)?"
- codex-invoked: "This Codex chat has no explicit Codex peer, so the Claude-watcher flow applies. This chat stays idle until you bootstrap it: the watcher chat will give you a one-line \"Read <inbox path> and follow it.\" instruction — paste it here. Nothing happens in this chat until you paste it."
- codex-first-paste: "Please paste into the Codex chat: \"Read {INBOX} and follow it.\""
- codex-nudge: "The Codex implementer's watch has ended. Please type in the Codex chat: \"check the inbox\"."
- codex-watcher-nudge: "The Codex watcher's watch has ended. Please type in the watcher chat: \"check the outbox\"."
- standby-wait: "Standby noted. This chat will not search for the peer; the active chat will contact it. Waiting."
- no-peer: "No peer session found (or no reply within 15 minutes). Is the other chat started? Waiting for your instruction."
- peer-silent: "The peer has been unresponsive for over 30 minutes. Observed facts: {FACTS}. Stopping here."
