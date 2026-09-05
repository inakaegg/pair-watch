#!/usr/bin/env python3
"""Validate the shared plugin package without requiring either coding CLI."""
import json
from pathlib import Path
import re
import sys


def validate(root):
    root = Path(root).resolve()
    def load(path):
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError(f'{path}: expected object')
        return value
    def inside(base, relative):
        if not isinstance(relative, str) or not relative.startswith('./'):
            raise ValueError('source must be ./relative/path')
        path = (base / relative).resolve(strict=True)
        if not path.is_relative_to(base):
            raise ValueError('source escapes package root')
        return path
    manifests = []
    for folder, catalog_path in [('.claude-plugin','.claude-plugin/marketplace.json'),
                                 ('.codex-plugin','.agents/plugins/marketplace.json')]:
        catalog = load(root/catalog_path)
        if catalog.get('name') != 'pair-watch' or not isinstance(catalog.get('plugins'),list):
            raise ValueError('invalid marketplace')
        entries = [e for e in catalog['plugins'] if e.get('name') == 'pair-watch']
        if len(entries) != 1:
            raise ValueError('marketplace must list pair-watch exactly once')
        source = entries[0]['source']
        if folder == '.codex-plugin':
            if source.get('source') != 'local':
                raise ValueError('expected local Codex source')
            source = source['path']
        plugin = inside(root,source)
        manifest = load(plugin/folder/'plugin.json')
        if manifest.get('name') != 'pair-watch' or not re.fullmatch(r'\d+\.\d+\.\d+',manifest.get('version','')):
            raise ValueError('invalid plugin identity')
        if not manifest.get('description'):
            raise ValueError('description required')
        skills = inside(plugin, manifest.get('skills','./skills'))
        if not (skills/'pair-watch/SKILL.md').is_file():
            raise ValueError('missing skill')
        hook = load(plugin/'hooks/hooks.json')
        if not hook.get('hooks',{}).get('SessionStart'):
            raise ValueError('missing SessionStart hook')
        manifests.append(manifest)
    if manifests[0]['version'] != manifests[1]['version']:
        raise ValueError('plugin versions disagree')


if __name__ == '__main__':
    try:
        validate(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as e:
        sys.exit(f'package validation failed: {e}')
    print('PASS: Claude and Codex package manifests and paths')
