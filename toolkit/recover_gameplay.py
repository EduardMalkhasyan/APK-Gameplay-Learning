import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def tool_command(path):
    return ['dotnet', str(path)] if path.suffix.lower() == '.dll' else [str(path)]


def run(command, log, environment, limit, allowed_codes=(0,)):
    with log.open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, env=environment, timeout=limit)
    if result.returncode not in allowed_codes:
        raise RuntimeError(f'Tool failed with exit {result.returncode}; inspect {log}')


def extract_input(input_path, work):
    archives = []
    with zipfile.ZipFile(input_path) as outer:
        entries = [entry for entry in outer.infolist() if entry.filename.lower().endswith('.apk')]
        if entries:
            for index, entry in enumerate(entries):
                path = work / f'split-{index}.apk'
                with outer.open(entry) as source, path.open('wb') as target:
                    shutil.copyfileobj(source, target)
                archives.append(path)
        else:
            archives.append(input_path)
    metadata = None
    binaries = []
    assemblies = {}
    unity_version = None
    for archive_path in archives:
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                filename = entry.filename
                basename = Path(filename).name
                if basename == 'global-metadata.dat':
                    metadata = work / basename
                    metadata.write_bytes(archive.read(entry))
                elif basename == 'libil2cpp.so':
                    destination = work / (filename.replace('/', '-') + '.bin')
                    with archive.open(entry) as source, destination.open('wb') as target:
                        shutil.copyfileobj(source, target)
                    rank = next((value for abi, value in [('arm64-v8a', 0), ('x86_64', 1), ('armeabi-v7a', 2), ('x86', 3)] if f'/{abi}/' in filename), 10)
                    binaries.append((rank, filename, destination))
                elif '/Managed/' in filename and basename.endswith('.dll'):
                    destination = work / 'mono' / basename
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(archive.read(entry))
                    assemblies[basename] = destination
                if basename in {'data.unity3d', 'globalgamemanagers'}:
                    with archive.open(entry) as stream:
                        header = stream.read(8192)
                    match = re.search(rb'(?:20\d{2}|6000)\.\d+\.\d+[abfp]\d+', header)
                    if match:
                        unity_version = match.group().decode('ascii')
    if binaries and metadata:
        magic, version = struct.unpack_from('<II', metadata.read_bytes())
        if magic != 0xFAB11BAF:
            raise RuntimeError('Metadata header is unsupported or protected; no source reconstruction claimed')
        _, abi, binary = sorted(binaries)[0]
        return {'backend': 'IL2CPP', 'binary': binary, 'binary_entry': abi, 'metadata': metadata, 'metadata_version': version, 'unity_version': unity_version}
    if 'Assembly-CSharp.dll' in assemblies:
        return {'backend': 'Mono', 'assemblies': assemblies, 'unity_version': unity_version}
    raise RuntimeError('No supported Unity IL2CPP binary/metadata pair or managed Assembly-CSharp.dll found')


def included(path, prefixes):
    source = path.read_text(errors='replace')
    match = re.search(r'^\s*namespace\s+([\w.]+)', source, re.MULTILINE)
    namespace = match.group(1) if match else ''
    if prefixes:
        return any(namespace == prefix or namespace.startswith(prefix + '.') for prefix in prefixes)
    vendor = ['UnityEngine', 'UnityEditor', 'System', 'Microsoft', 'Cpp2ILInjected', 'Sirenix', 'Zenject', 'Pathfinding', 'Firebase', 'Google', 'Appodeal', 'AppsFlyer', 'Facebook', 'DG.Tweening', 'TMPro', 'Newtonsoft', 'Cysharp', 'UniRx', 'Bitgem']
    return not any(namespace == prefix or namespace.startswith(prefix + '.') for prefix in vendor) and path.name != 'UnitySourceGeneratedAssemblyMonoScriptTypes_v1.cs'


def main():
    parser = argparse.ArgumentParser(description='Recover Unity gameplay C# with explicit incomplete/unverified status')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cpp2il', type=Path, default=Path(__file__).resolve().parent / 'Engine' / 'Cpp2IL.dll')
    parser.add_argument('--ilspy', type=Path, default=Path(__file__).resolve().parent / 'ILSpy' / 'ilspycmd.dll')
    parser.add_argument('--unity-version')
    parser.add_argument('--assemblies', default='Assembly-CSharp')
    parser.add_argument('--include-namespace', action='append', default=[])
    parser.add_argument('--budget', type=int, default=180, help='seconds allowed for each tool run; large binaries need more')
    options = parser.parse_args()
    input_path = options.input.resolve(strict=True)
    output = options.output.resolve()
    if output.exists():
        raise RuntimeError('Output already exists; use a new directory to preserve existing work')
    if options.ilspy.exists() == False:
        raise RuntimeError('ILSpy executable/DLL is missing')
    output.mkdir(parents=True)
    evidence = output / 'Evidence'
    evidence.mkdir()
    environment = os.environ.copy()
    environment['DOTNET_PROCESSOR_COUNT'] = '4'
    names = [name.strip() for name in options.assemblies.split(',') if name.strip()]
    with tempfile.TemporaryDirectory(prefix='apk-gameplay-') as directory:
        work = Path(directory)
        info = extract_input(input_path, work)
        if info['backend'] == 'IL2CPP':
            if options.cpp2il is None or options.cpp2il.exists() == False:
                raise RuntimeError('IL2CPP input requires --cpp2il pointing to a body-recovering, patched tool')
            version = options.unity_version or info['unity_version']
            if version is None:
                raise RuntimeError('Unity version unavailable; provide --unity-version')
            dll_directory = work / 'dlls'
            environment['DOTNET_BUNDLE_EXTRACT_BASE_DIR'] = str(work / 'bundle')
            environment['TOOLKIT_RECOVERY_ASSEMBLIES'] = ','.join(names)
            environment['RECOVERY_METHOD_MAP_PATH'] = str(evidence / 'method-map.tsv')
            command = tool_command(options.cpp2il.resolve()) + ['--force-binary-path', str(info['binary']), '--force-metadata-path', str(info['metadata']), '--force-unity-version', version, '--use-processor', 'attributeanalyzer', '--output-as', 'dll_il_recovery', '--output-to', str(dll_directory)]
            run(command, evidence / 'cpp2il.log', environment, options.budget)
            assemblies = {name + '.dll': dll_directory / (name + '.dll') for name in names}
        else:
            version = options.unity_version or info['unity_version']
            assemblies = info['assemblies']
        files = []
        missing = []
        export_errors = 0
        for name in names:
            assembly = assemblies.get(name + '.dll')
            if assembly is None or assembly.exists() == False:
                missing.append(name)
                continue
            export = work / ('csharp-' + name)
            log = evidence / (name + '-ilspy.log')
            run(tool_command(options.ilspy.resolve()) + ['-p', '-o', str(export), str(assembly)], log, environment, options.budget, allowed_codes=(0, 70))
            if export.exists() == False or any(export.rglob('*.cs')) == False:
                raise RuntimeError(f'ILSpy produced no source; inspect {log}')
            export_errors += log.read_text(errors='replace').count('Error decompiling')
            for source in sorted(export.rglob('*.cs')):
                if included(source, options.include_namespace) == False:
                    continue
                relative = Path(name) / source.relative_to(export)
                destination = output / 'DecompiledGameplay' / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                text = source.read_text(errors='replace')
                diagnostics = text.count('NoteDecompilerIssue(')
                warnings = len(re.findall(r'//IL_[0-9a-fA-F]+:', text))
                invalid_identifier = bool(re.search(r'\b(?:\w+__BackingField|System\.Int32Enum)\b', text))
                exceptions = bool(re.search(r'\breturn[^;\n]*\)ex\w*\b', text))
                placeholders = len(re.findall(r'\bthrow\s+null\s*;', text))
                files.append({'file': str(relative), 'sha256': sha256(destination), 'diagnostic_calls': diagnostics, 'il_warning_comments': warnings, 'backing_field_or_enum_artifacts': invalid_identifier, 'suspect_exception_return': exceptions, 'placeholder_throws': placeholders, 'status': 'incomplete' if diagnostics or warnings or invalid_identifier or exceptions or placeholders else 'unverified'})
        if len(missing) == len(names):
            raise RuntimeError('None of the requested assemblies was produced: ' + ', '.join(names))
        blocked = bool(missing) or export_errors > 0 or any(item['status'] == 'incomplete' for item in files)
        report = {'input': input_path.name, 'input_sha256': sha256(input_path), 'backend': info['backend'], 'unity_version': version, 'metadata_version': info.get('metadata_version'), 'native_binary_sha256': sha256(info['binary']) if info['backend'] == 'IL2CPP' else None, 'cpp2il_sha256': sha256(options.cpp2il) if options.cpp2il else None, 'cpp2il_core_sha256': sha256(options.cpp2il.parent / 'Cpp2IL.Core.dll') if options.cpp2il and (options.cpp2il.parent / 'Cpp2IL.Core.dll').exists() else None, 'ilspy_sha256': sha256(options.ilspy), 'file_count': len(files), 'missing_assemblies': missing, 'ilspy_method_errors': export_errors, 'quality_gate': 'blocked' if blocked else 'unverified', 'original_source_recovered': False, 'native_equivalence_verified': False, 'method_address_evidence': (evidence / 'method-map.tsv').exists(), 'files': files}
        (output / 'quality.json').write_text(json.dumps(report, indent=2))
        (output / 'README.md').write_text('APK-derived decompiler output. This is not exact original source or a verified working project. Read quality.json before using any method. No diagnostic-free file is automatically classified as correct. Native-address evidence is included when the patched engine supports it. Vendor filtering is heuristic; use --include-namespace for explicit scope.\n')
        print(json.dumps({key: report[key] for key in ['file_count', 'ilspy_method_errors', 'quality_gate', 'native_equivalence_verified']}))
        return 2 if blocked else 0


if __name__ == '__main__':
    raise SystemExit(main())
