"""Read-only runtime/ABI inventory. Signals are hints, never recovered gameplay."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_package(path):
    path = Path(path).resolve(strict=True)
    report = {'input': str(path), 'sha256': fingerprint(path),
              'container': None, 'archives': [], 'architectures': [],
              'runtime_signals': {}, 'payloads': {'dex': [], 'managed': [], 'native': []},
              'warnings': [], 'original_source_recovered': False,
              'native_equivalence_verified': False}
    architectures = set()

    def signal(runtime, location):
        report['runtime_signals'].setdefault(runtime, []).append(location)

    def scan(archive, label):
        report['archives'].append(label)
        for entry in archive.infolist():
            name = entry.filename
            location = label + '!/' + name
            lower = name.lower()
            basename = Path(name).name.lower()
            parts = name.split('/')
            if 'lib' in parts:
                index = parts.index('lib')
                if index + 2 < len(parts):
                    abi = parts[index + 1]
                    if abi in {'arm64-v8a', 'armeabi-v7a', 'armeabi', 'x86', 'x86_64', 'riscv64'}:
                        architectures.add(abi)
            if lower.endswith('.so'):
                report['payloads']['native'].append(location)
            if lower.endswith('.dex'):
                report['payloads']['dex'].append(location)
            if '/managed/' in lower and lower.endswith('.dll'):
                report['payloads']['managed'].append(location)
                signal('unity_managed', location)
            if basename in {'libil2cpp.so', 'global-metadata.dat'}:
                signal('unity_il2cpp', location)
            if basename == 'libunity.so' or '/assets/bin/data/' in '/' + lower:
                signal('unity', location)
            if basename == 'libflutter.so' or 'flutter_assets/' in lower:
                # Record a marker once rather than every image/sound asset.
                existing = report['runtime_signals'].get('flutter', [])
                if basename == 'libflutter.so' or not any(x.startswith(label + '!/') for x in existing):
                    signal('flutter', location)
            if 'godot' in basename and lower.endswith('.so') or lower.endswith('.pck'):
                signal('godot', location)
            if basename in {'libue4.so', 'libunreal.so'}:
                signal('unreal', location)
            if 'cocos' in basename and lower.endswith('.so'):
                signal('cocos', location)
            if lower.endswith(('.lua', '.luac', '.wasm')) or '/assets/www/' in '/' + lower:
                signal('script_or_web', location)

    if zipfile.is_zipfile(path):
        report['container'] = 'zip-package'
        with zipfile.ZipFile(path) as archive:
            scan(archive, path.name)
            # APK splits are scanned from private spooled files, never extracted
            # by their untrusted filenames. Only one nesting level is inspected.
            for entry in archive.infolist():
                if not entry.filename.lower().endswith('.apk'):
                    continue
                if entry.file_size > 2 * 1024**3:
                    report['warnings'].append('Skipped split larger than 2 GiB: ' + entry.filename)
                    continue
                with tempfile.SpooledTemporaryFile(max_size=16 * 1024**2) as split:
                    with archive.open(entry) as source:
                        shutil.copyfileobj(source, split)
                    split.seek(0)
                    if zipfile.is_zipfile(split):
                        with zipfile.ZipFile(split) as nested:
                            scan(nested, path.name + '!/' + entry.filename)
                    else:
                        report['warnings'].append('Invalid nested APK: ' + entry.filename)
    else:
        with path.open('rb') as stream:
            header = stream.read(64)
        if len(header) >= 20 and header[:4] == b'\x7fELF' and header[5] in (1, 2):
            report['container'] = 'elf'
            endian = '<' if header[5] == 1 else '>'
            machine = struct.unpack_from(endian + 'H', header, 18)[0]
            architectures.add({40: 'ARM32', 183: 'ARM64', 3: 'x86', 62: 'x86_64'}.get(machine, 'ELF-machine-' + str(machine)))
            report['elf_bits'] = {1: 32, 2: 64}.get(header[4])
            report['warnings'].append('ELF header identifies architecture only; runtime and version need further inspection.')
        else:
            report['container'] = 'unknown'
            report['warnings'].append('No supported archive or ELF header; inspect the format manually.')
    report['architectures'] = sorted(architectures)
    if not report['runtime_signals']:
        report['warnings'].append('No recognized runtime markers. DEX/native payloads are not proof of a specific game engine.')
    report['next_step'] = 'Match the files against the engine table in docs/METHOD.md; verify runtime version and tool compatibility before exporting.'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_package(args.input), indent=2))
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        parser.exit(2, f'Inventory failed: {exc}\n')


if __name__ == '__main__':
    main()
