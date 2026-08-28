#!/usr/bin/env bash
# SessionStart hook: warn when the installed plugin cache is behind its
# marketplace source, so the assistant can offer the update to the user.
# Must never break session start: on any missing file or parse error, stay
# silent and exit 0.
set -u

root="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$root" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$root" <<'PY' 2>/dev/null || exit 0
import json
import os
import sys

root = sys.argv[1]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


try:
    own = load(os.path.join(root, ".claude-plugin", "plugin.json"))
except (OSError, ValueError):
    sys.exit(0)
name = own.get("name")
installed = own.get("version")
if not name or not installed:
    sys.exit(0)


def parse_version(value):
    parts = str(value).split(".")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


installed_tuple = parse_version(installed)
if installed_tuple is None:
    sys.exit(0)

# Find the marketplace that serves this plugin and read the live version.
known = os.path.join(
    os.path.expanduser("~"), ".claude", "plugins", "known_marketplaces.json"
)
try:
    marketplaces = load(known)
except (OSError, ValueError):
    sys.exit(0)

for market_name, market in marketplaces.items():
    location = market.get("installLocation")
    if not location:
        continue
    try:
        catalog = load(
            os.path.join(location, ".claude-plugin", "marketplace.json")
        )
    except (OSError, ValueError):
        continue
    for entry in catalog.get("plugins", []):
        if entry.get("name") != name:
            continue
        source = entry.get("source")
        if not isinstance(source, str):
            continue
        try:
            live = load(
                os.path.join(location, source, ".claude-plugin", "plugin.json")
            )
        except (OSError, ValueError):
            continue
        live_tuple = parse_version(live.get("version"))
        # Warn only when the installed copy is BEHIND the source; a newer
        # installed copy (e.g. the source checkout sits on an older branch)
        # must not trigger a downgrade suggestion.
        if live_tuple is not None and installed_tuple < live_tuple:
            live_version = live.get("version")
            print(
                f"[{name} plugin] The installed copy is {installed} but the "
                f"marketplace source ({market_name}) is at {live_version}. "
                "Behavior may not match the current source. Suggest to the "
                "user that they update, and offer to run: "
                f"claude plugin marketplace update {market_name} && "
                f"claude plugin update {name}@{market_name} "
                "(takes effect from the next session)."
            )
        sys.exit(0)
sys.exit(0)
PY
exit 0
