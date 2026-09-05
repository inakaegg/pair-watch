#!/usr/bin/env python3
"""Select explicit model settings without launching either provider."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--primary', choices=['codex', 'claude'], required=True)
    p.add_argument('--role', choices=['implementer', 'reviewer'], required=True)
    p.add_argument('--unavailable', action='append', default=[])
    p.add_argument('--codex-bin', default='codex')
    p.add_argument('--claude-bin', default='claude')
    a = p.parse_args()
    try:
        source = Path(__file__).resolve().parent.parent / 'references/model-defaults.json'
        config = json.loads(source.read_text())
        override = a.repo / 'pair-watch.settings.json'
        if override.exists():
            # A role replaces its entire ordered list; omitted roles retain the bundle's defaults.
            overrides = json.loads(override.read_text())
            config.update(overrides)
            if a.role in overrides:
                source = override
        candidates = config[a.role][a.primary] if a.role == 'implementer' else config[a.role]
        if not isinstance(candidates, list) or not candidates:
            raise ValueError('role must have a nonempty candidate list')
        parsed = []
        for candidate in candidates:
            match = re.fullmatch(r'(codex|claude):([A-Za-z0-9][A-Za-z0-9._/-]*)\(([a-z]+)\)', candidate)
            if not match:
                raise ValueError('use CLI:MODEL(EFFORT) for every candidate')
            parsed.append((candidate, *match.groups()))
        if a.role == 'reviewer':
            # The reviewer list is one list for both CLIs; the primary CLI's entries go first so the
            # session's own subscription is used, and the written order decides within each CLI.
            # Done after parsing so malformed entries still fail as invalid settings (exit 2).
            parsed = [p for p in parsed if p[1] == a.primary] + [p for p in parsed if p[1] != a.primary]
        unavailable = {}
        for item in a.unavailable:
            candidate, _, reason = item.partition('=')
            if candidate not in candidates or reason not in ['authentication', 'model-unavailable', 'rate-limit']:
                raise ValueError('unavailable must name a configured candidate and a recognized availability reason')
            unavailable[candidate] = reason
        skipped = []
        for candidate, cli, model, effort in parsed:
            binary = shutil.which(getattr(a, cli + '_bin'))
            reason = unavailable.get(candidate) or ('missing-cli' if binary is None else None)
            if reason:
                skipped.append(dict(candidate=candidate, reason=reason))
                continue
            print(json.dumps(dict(status='selected', candidate=candidate, cli=cli, binary=binary,
                                  model=model, effort=effort, source=str(source), skipped=skipped)))
            return 0
        print(json.dumps(dict(status='unavailable', source=str(source), skipped=skipped)))
        return 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps(dict(status='invalid-settings', error=str(error))))
        return 2


if __name__ == '__main__':
    sys.exit(main())
