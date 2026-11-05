"""Unpack an APK/XAPK/APKS/APKM into a work folder, treating it as a hostile archive.

Writes splits/ (the bundle's own entries) and unzipped/ (every split merged, first
file wins) under the output folder. Refuses entries that would land outside the
target, skips symlinks, caps the bytes written and stops on a time budget. It never
runs anything from the package. Standard library only.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import time
import zipfile

REPOSITORY = Path(__file__).resolve().parent.parent
CHUNK = 1024 * 1024


class Budget:
    def __init__(self, max_bytes, seconds):
        self.max_bytes = max_bytes
        self.deadline = time.monotonic() + seconds
        self.written = 0

    def charge(self, count):
        self.written += count
        if self.written > self.max_bytes:
            raise RuntimeError(f'Byte cap exceeded ({self.max_bytes} bytes); is this a decompression bomb?')
        if time.monotonic() > self.deadline:
            raise RuntimeError('Time budget exceeded')


def safe_target(root, name):
    """The path an entry may be written to, or None when the name is unsafe."""
    pure = PurePosixPath(name.replace('\\', '/'))
    if pure.is_absolute() or '..' in pure.parts or not pure.parts:
        return None
    target = root.joinpath(*pure.parts)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return target


def extract(archive, root, budget, report, overwrite=False):
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        if stat.S_ISLNK(entry.external_attr >> 16):
            report['skipped'].append({'entry': entry.filename, 'reason': 'symlink'})
            continue
        target = safe_target(root, entry.filename)
        if target is None:
            report['skipped'].append({'entry': entry.filename, 'reason': 'unsafe path'})
            continue
        if target.exists() and not overwrite:
            report['collisions'] += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(entry) as source, target.open('wb') as sink:
            while True:
                block = source.read(CHUNK)
                if not block:
                    break
                budget.charge(len(block))
                sink.write(block)
        report['files'] += 1


def holds_code(path):
    if not path.is_file() or not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as archive:
        return 'classes.dex' in archive.namelist()


def unpack(package, output, max_bytes=16 * 1024**3, seconds=900):
    package = Path(package).resolve(strict=True)
    output = Path(output).resolve()
    try:
        output.relative_to(REPOSITORY)
    except ValueError:
        pass
    else:
        raise ValueError('The output folder must be outside this repository')
    splits = output / 'splits'
    merged = output / 'unzipped'
    splits.mkdir(parents=True, exist_ok=True)
    merged.mkdir(parents=True, exist_ok=True)
    budget = Budget(max_bytes, seconds)
    report = {'input': str(package), 'container': None, 'splits': [], 'files': 0,
              'collisions': 0, 'skipped': [], 'warnings': []}
    if not zipfile.is_zipfile(package):
        raise ValueError('Not a ZIP-based package')
    with zipfile.ZipFile(package) as outer:
        names = [entry.filename for entry in outer.infolist()]
        nested = [name for name in names if name.lower().endswith(('.apk', '.obb'))]
        if 'AndroidManifest.xml' in names and not nested:
            report['container'] = 'apk'
            report['splits'].append(package.name)
            extract(outer, merged, budget, report)
        else:
            report['container'] = 'bundle'
            extract(outer, splits, budget, report)
    if report['container'] == 'bundle':
        # The base holds classes.dex and goes first, so an asset pack or config split can never shadow its manifest.
        order = sorted(splits.rglob('*'), key=lambda p: (not holds_code(p), 'config.' in p.name, p.name))
        for member in order:
            if not member.is_file() or member.suffix.lower() not in {'.apk', '.obb'}:
                continue
            if not zipfile.is_zipfile(member):
                report['warnings'].append('Not a ZIP, left in splits/: ' + member.name)
                continue
            with zipfile.ZipFile(member) as inner:
                extract(inner, merged, budget, report)
            report['splits'].append(member.name)
    report['bytes_written'] = budget.written
    if not (merged / 'assets').exists():
        report['warnings'].append('No assets/ folder after unpacking: the bundle may be incomplete.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--max-bytes', type=int, default=16 * 1024**3)
    parser.add_argument('--budget', type=int, default=900, help='seconds')
    args = parser.parse_args()
    try:
        report = unpack(args.package, args.output, args.max_bytes, args.budget)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        shutil.rmtree(args.output / 'unzipped', ignore_errors=True)
        parser.exit(2, f'Unpack failed: {exc}\n')
    json.dump(report, sys.stdout, indent=2)
    print()


if __name__ == '__main__':
    main()
