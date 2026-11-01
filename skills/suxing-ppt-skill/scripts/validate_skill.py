#!/usr/bin/env python3
"""Validate the portable skill layout without external dependencies.

Not an official Agent Skills certification; see https://agentskills.io/specification.
"""
import argparse
import re
import sys
from pathlib import Path

PATTERN = re.compile(r"\]\(([^)]+)\)")


def validate(root):
    root = Path(root).resolve()
    errors = []
    skill = root / 'SKILL.md'
    if not skill.is_file():
        return ['SKILL.md is missing']
    body = skill.read_text(encoding='utf-8-sig')
    if not body.startswith('---\n') or '\n---\n' not in body[4:]:
        return ['SKILL.md must start with YAML frontmatter delimited by ---']
    _, head, content = body.split('---', 2)
    fields = {}
    for line in head.strip().splitlines():
        m = re.match(r'^([\w-]+):\s*(.*)$', line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"\'')
    name = fields.get('name', '')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 64:
        errors.append('Invalid skill name: use lowercase letters, digits and single hyphens (<=64)')
    if name != root.name:
        errors.append(f'Skill directory name ({root.name}) must equal frontmatter name ({name})')
    if not fields.get('description') or len(fields.get('description', '')) > 1024:
        errors.append('description missing or longer than 1024 chars')
    if not content.strip():
        errors.append('SKILL.md instruction body is empty')
    for item in root.rglob('*.md'):
        text = item.read_text(encoding='utf-8')
        for match in PATTERN.findall(text):
            url = match.split(' ', 1)[0].split('#', 1)[0].strip('<>')
            if not url or '://' in url or url.startswith(('mailto:', '#', '/')):
                continue
            if not (item.parent / url).exists():
                errors.append(f'{item.relative_to(root)}: broken link: {url}')
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', nargs='?', default='.')
    args = ap.parse_args()
    errors = validate(args.root)
    if errors:
        for error in errors:
            print('FAIL:', error, file=sys.stderr)
        sys.exit(1)
    print('PASS: SKILL.md frontmatter, name, instruction body, and local markdown links')


if __name__ == '__main__':
    main()
