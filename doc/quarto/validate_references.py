#!/usr/bin/env python3
"""
Sadly quarto doesn't have builtin reference validation?
See https://github.com/quarto-dev/quarto-cli/discussions/13259
"""

# TODO validate file links as well?
import re
import sys
from pathlib import Path

defs = {}
refs = []
relative_links = []

path = Path(sys.argv[1])
for i, line in enumerate(path.read_text().splitlines()):
    lineno = i + 1
    # FIXME might be multiple per line?
    ## cross-reference definition
    m = re.search(r'\{(#\S+)\}', line)
    if m is not None:
        xx = m.group(1)
        assert xx not in defs, (xx, defs)
        defs[xx] = (lineno, line)
        continue
    ## cross-reference usage
    m = re.search(r'\((#\S+)\)', line)
    if m is not None:
        xx = m.group(1)
        refs.append((xx, lineno, line))
        continue
    m = re.search(r'\]\((\S+)\)', line)
    if m is not None:
        url = m.group(1)
        if not url.startswith(('http://', 'https://')):
            relative_links.append((url, lineno, line))


errors = []
for ref, lineno, line in refs:
    if ref in defs:
        continue
    print(f"{path}:{lineno}: reference {ref} not found\n  {line}", file=sys.stderr)
    errors.append(ref)

for url, lineno, line in relative_links:
    relpath = Path(url)
    if not relpath.exists():
        print(f"{path}:{lineno}: link {url} not found\n  {line}", file=sys.stderr)
        errors.append(url)

assert len(errors) == 0
