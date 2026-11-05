"""Compare two JSON files, for example the config bundled in a package and the copy a game saved on the device.

python3 toolkit/live/diff_json.py bundled.json device.json [--limit 200]

Prints one line per added, removed or changed value. JSON stored inside strings is compared as JSON.
Anything shaped like a key, token or ad unit id is masked. Standard library only.
"""
import argparse
import json
from pathlib import Path
import re

SECRET = re.compile(r'\b[A-Za-z0-9_+/=-]{14,}\b')


def mask(value):
    return SECRET.sub(lambda match: match.group(0)[:3] + '...', str(value))


def parse(value):
    if isinstance(value, str) and value[:1] in '{[':
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def diff(old, new, path=''):
    """Yield (path, old, new) for every difference; a missing side is None."""
    old, new = parse(old), parse(new)
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new), key=str):
            yield from diff(old.get(key), new.get(key), f'{path}/{key}')
    elif isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        for index, (left, right) in enumerate(zip(old, new)):
            yield from diff(left, right, f'{path}[{index}]')
    elif old != new:
        yield path, old, new


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('old', type=Path)
    parser.add_argument('new', type=Path)
    parser.add_argument('--limit', type=int, default=200)
    args = parser.parse_args()
    changes = list(diff(json.loads(args.old.read_bytes()), json.loads(args.new.read_bytes())))
    print(f'{len(changes)} differences')
    for path, old, new in changes[:args.limit]:
        print(f'{path}: {mask(json.dumps(old))[:80]} -> {mask(json.dumps(new))[:120]}')


if __name__ == '__main__':
    main()
