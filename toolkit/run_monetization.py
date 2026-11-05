"""One command for the monetization route: packages in, evidence folders out.

For each package: inventory, safe unpack, scan, script values, code recovery and Java
decompilation, one heavy tool at a time. Steps that already produced output are kept, so a
stopped run can resume. Each game gets EVIDENCE.md saying what worked and where to start
reading. Nothing from a package is executed. The output must be outside this repository.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
PACKAGE_SUFFIXES = {'.apk', '.xapk', '.apks', '.apkm'}
DEFAULT_UNITYPY = Path.home() / '.venvs/unitypy/bin/python'
UNITY_VERSION = re.compile(rb'(?:20\d{2}|6000)\.\d+\.\d+[abfp]\d+')
# Assemblies that never hold a game's own monetization logic. Publisher layers stay in.
VENDOR_ASSEMBLIES = re.compile(
    r'^(System|Mono\.|mscorlib|netstandard|UnityEngine|UnityEditor|Unity\.|Microsoft\.|nunit|DOTween|DemiLib|'
    r'Newtonsoft|TextMeshPro|Cinemachine|Sirenix|UniTask|UniRx|R3|ZLinq|ZString|MessagePack|MessagePipe|protobuf|'
    r'Google\.|Firebase\.|Facebook\.|AppsFlyer|AWSSDK|SkiaSharp|Spine|Lean|JetBrains|Febucci|Ionic|ICSharpCode|'
    r'BouncyCastle|Coffee|StompyRobot|LeTai|NaughtyAttributes|ToonyColorsPro|KinoBloom|Doozy|EasySave|OSA\.|'
    r'Bitsplash|GraphAndChart|PlayFab|Nakama|VContainer|Animancer|Autodesk|MCPForUnity|NativeShare|NativeGallery|'
    r'LottiePlugin|IngameDebugConsole|HighlightPlus|SplinePower|UIGradient|UnityPlayModeSaver|StoreScreenshot|'
    r'DynamicExpresso|ObservableCollections|ScriptableObject-Architecture|Lofelt|NiceVibrations|AppleAuth|GoogleSignin)')
MONEY_CLASS = re.compile(
    r'(?i)(iap|purchas|product|offer|shop|store|premium|vip|subscri|pass\b|pass[A-Z]|piggy|bank|bundle|pack\b|reward|'
    r'(^|\.)ads?[A-Z.]|Ads?(Button|Manager|Service|Config|Settings|Data|View)|AD[A-Z][a-z]|segment|remote|currency|balance)')
NOT_CONFIG = re.compile(r'(?i)(mraid|bridge|monitor|binddatas|download_dialog|google-services|UnityServices)')


def find_packages(paths):
    found = []
    for path in paths:
        path = Path(path).expanduser()
        if path.is_dir():
            found.extend(sorted(item for item in path.iterdir() if item.suffix.lower() in PACKAGE_SUFFIXES))
        elif path.suffix.lower() in PACKAGE_SUFFIXES:
            found.append(path)
        else:
            raise ValueError(f'Not a package or folder: {path}')
    return found


def slug_from_filename(name):
    stem = Path(name).stem.replace('+', ' ')
    stem = re.split(r'_\s*v?\d+(?:\.\d+)+', stem)[0]
    return re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-') or 'package'


def app_assemblies(names, limit=80):
    """Assembly names worth recovering, game code first."""
    stems = [name[:-4] if name.endswith('.dll') else name for name in names]
    kept = [name for name in stems if not VENDOR_ASSEMBLIES.match(name)]
    kept.sort(key=lambda name: (not name.startswith('Assembly-CSharp'), name))
    return kept[:limit]


def describe(unzipped):
    """What the unpacked package is, from its files alone."""
    data = unzipped / 'assets/bin/Data'
    info = {'backend': 'not Unity', 'abi': None, 'library': None, 'metadata': None, 'unity_version': None, 'assemblies': []}
    for name in ('data.unity3d', 'globalgamemanagers'):
        path = data / name
        if path.is_file():
            with path.open('rb') as stream:
                match = UNITY_VERSION.search(stream.read(8192))
            if match:
                info['unity_version'] = match.group().decode('ascii')
                break
    listing = data / 'ScriptingAssemblies.json'
    if listing.is_file():
        try:
            info['assemblies'] = json.loads(listing.read_text(errors='replace')).get('names', [])
        except ValueError:
            pass
    metadata = data / 'Managed/Metadata/global-metadata.dat'
    for abi in ('arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86'):
        library = unzipped / 'lib' / abi / 'libil2cpp.so'
        if library.is_file() and metadata.is_file():
            info.update(backend='il2cpp', abi=abi, library=library, metadata=metadata)
            return info
    if (data / 'Managed/Assembly-CSharp.dll').is_file():
        info['backend'] = 'mono'
    return info


def build_warnings(manifest, sdks, info):
    warnings = []
    mediation = (sdks or {}).get('mediation', {})
    dead = [name for name in mediation if 'legacy' in name]
    if dead:
        warnings.append(f'Dead mediator in this build ({", ".join(dead)}): it is years old. Check package and version against the store before analysing.')
    target = (manifest or {}).get('targetSdk')
    if isinstance(target, int) and target < 33:
        warnings.append(f'Target SDK {target} is old: this build is unlikely to be the live one.')
    if info['backend'] == 'il2cpp' and info['abi'] != 'arm64-v8a':
        warnings.append(f'Only {info["abi"]} is present: expect names without method bodies. Ask for the bundle with the arm64 split.')
    if info['backend'] == 'not Unity':
        warnings.append('No Unity runtime found: the scan still applies, but pick the code route from docs/ENGINE_ROUTES.md.')
    return warnings


def money_classes(folder):
    """Script classes in the exported values that look monetization-related, with counts."""
    counts = collections.Counter()
    for sub in ('MonoBehaviour', 'MonoBehaviourStrings'):
        path = folder / sub
        if not path.is_dir():
            continue
        for item in path.iterdir():
            with item.open(errors='replace') as stream:
                match = re.search(r'"_script": "([^"]*)"', stream.read(200))
            if match:
                counts[match.group(1)] += 1
    return [(name, count) for name, count in counts.most_common() if MONEY_CLASS.search(name)]


def has_output(path):
    return path.is_file() and path.stat().st_size > 0 or path.is_dir() and any(path.iterdir())


class Steps:
    def __init__(self, force):
        self.force = force
        self.rows = []

    def note(self, name, result):
        self.rows.append({'step': name, 'result': result})
        print(f'  {name}: {result}', flush=True)

    def run(self, name, command, log, budget, output=None, ok=(0,), env=None, cwd=None, clean=None):
        """Runs one tool. Returns True when its output can be used.

        A failed step leaves a marker, so its partial output is rebuilt on resume, never trusted.
        """
        output = output or log
        marker = log.with_name(log.name + '.failed')
        if not self.force and has_output(output) and not marker.exists():
            self.note(name, 'kept existing output')
            return True
        leftover = clean or output
        if leftover.is_dir():
            shutil.rmtree(leftover)
        log.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        try:
            with log.open('w') as stream:
                code = subprocess.run([str(part) for part in command], stdout=stream, stderr=subprocess.STDOUT,
                                      stdin=subprocess.DEVNULL, timeout=budget, env=env, cwd=cwd).returncode
        except subprocess.TimeoutExpired:
            code = f'stopped at the {budget} s budget'
        except OSError as exc:
            code = f'could not start: {exc}'
        passed = code in ok
        if passed:
            marker.unlink(missing_ok=True)
        else:
            marker.write_text(str(code))
        seconds = round(time.monotonic() - start)
        self.note(name, f'{"ok" if passed else "FAILED"} (exit {code}, {seconds} s, log {log.name})')
        return passed


def process(package, root, options):
    slug = options.slug or slug_from_filename(package.name)
    work = root / slug
    evidence, raw = work / 'evidence', work / 'raw'
    for folder in (evidence, raw, work / 'findings'):
        folder.mkdir(parents=True, exist_ok=True)
    print(f'{package.name} -> {work}', flush=True)
    steps = Steps(options.force)
    python = [sys.executable, '-I']
    steps.run('inventory', python + [HERE / 'inspect_package.py', package], evidence / 'inventory.json', 600)
    steps.run('unpack', python + [HERE / 'unpack_package.py', package, work], evidence / 'unpack.json', 1800,
              output=work / 'unzipped')
    unzipped = work / 'unzipped'
    if not has_output(unzipped):
        return {'slug': slug, 'package': package.name, 'steps': steps.rows, 'warnings': ['Unpacking failed: see evidence/unpack.json']}
    steps.run('scan', python + [HERE / 'scan_monetization.py', unzipped, evidence / 'scan'], evidence / 'scan.out', 900,
              output=evidence / 'scan/scan.json')

    info = describe(unzipped)
    assemblies = app_assemblies(info['assemblies'], options.max_assemblies)
    unitypy = Path(options.unitypy).expanduser()
    dotnet = shutil.which('dotnet')
    environment = dict(os.environ, DOTNET_PROCESSOR_COUNT='4')
    dll_folder = None
    if info['backend'] == 'il2cpp':
        arm64 = info['abi'] == 'arm64-v8a'
        if not dotnet:
            steps.note('assemblies', 'skipped: .NET 10 is not installed')
        elif not arm64 and not options.arm32_cpp2il:
            steps.note('assemblies', 'skipped on ARM32: too slow here (--arm32-cpp2il forces it, with native Capstone)')
        elif not info['unity_version']:
            steps.note('assemblies', 'skipped: Unity version not found')
        else:
            if not arm64:
                environment['DYLD_FALLBACK_LIBRARY_PATH'] = '/opt/homebrew/lib'
            target = raw / 'dummydll'
            passed = steps.run('assemblies', ['dotnet', HERE / 'Engine/Cpp2IL.dll', '--force-binary-path', info['library'],
                                              '--force-metadata-path', info['metadata'], '--force-unity-version', info['unity_version'],
                                              '--use-processor', 'attributeanalyzer,attributeinjector', '--output-as', 'dummydll',
                                              '--output-to', target],
                               evidence / 'cpp2il-dummy.log', options.budget, output=target, env=environment, cwd=raw)
            dll_folder = target if passed and has_output(target) else None
    elif info['backend'] == 'mono':
        dll_folder = unzipped / 'assets/bin/Data/Managed'

    if info['backend'] == 'not Unity':
        steps.note('values', 'skipped: not a Unity package')
    elif not unitypy.exists():
        steps.note('values', f'skipped: no UnityPy at {unitypy} (setup in docs/METHOD.md)')
    else:
        command = [unitypy, '-I', HERE / 'export_unity_assets.py', unzipped, raw / 'values', '--only', 'TextAsset,MonoBehaviour',
                   '--budget', options.budget, '--raw-strings']
        if dll_folder:
            command += ['--dll-folder', dll_folder]
        steps.run('values', command, evidence / 'values.out', options.budget + 60, output=raw / 'values')

    if info['backend'] == 'il2cpp' and info['abi'] != 'arm64-v8a':
        steps.note('code', 'skipped on ARM32: use evidence/scan/il2cpp_types.jsonl for names')
    elif info['backend'] in ('il2cpp', 'mono') and dotnet and assemblies:
        steps.run('code', python + [HERE / 'recover_gameplay.py', package, '--output', raw / 'code', '--assemblies', ','.join(assemblies),
                                    '--budget', options.budget],
                  evidence / 'recover.out', options.budget * 3, output=raw / 'code/quality.json', ok=(0, 2), env=environment,
                  clean=raw / 'code')

    scan_path = evidence / 'scan/scan.json'
    report = json.loads(scan_path.read_text()) if scan_path.exists() else {}
    publisher_dex = [item for item in sorted(report.get('publisher_dex', {}).items(), key=lambda item: -item[1]) if item[1] >= 30][:options.max_dex]
    if not shutil.which('jadx'):
        steps.note('java', 'skipped: jadx is not installed (brew install jadx)')
    elif publisher_dex:
        files = [unzipped / name for name, _ in publisher_dex]
        steps.run('java', ['jadx', '--no-res', '--no-imports', '--show-bad-code', '-j', '3', '-d', raw / 'jadx'] + files,
                  evidence / 'jadx.log', options.budget, output=raw / 'jadx', ok=(0, 3),
                  env=dict(os.environ, JAVA_OPTS='-Xmx6g'))
    result = {'slug': slug, 'package': package.name, 'info': {key: str(value) if isinstance(value, Path) else value for key, value in info.items() if key != 'assemblies'},
              'assemblies': assemblies, 'steps': steps.rows,
              'warnings': build_warnings(report.get('manifest'), report.get('sdks'), info) + report.get('warnings', [])}
    (evidence / 'status.json').write_text(json.dumps(result, indent=1))
    (work / 'EVIDENCE.md').write_text(evidence_page(work, result, report))
    return result


def evidence_page(work, result, report):
    manifest = report.get('manifest') or {}
    info = result.get('info', {})
    package_id = manifest.get('package')
    lines = [f'# Evidence: {package_id or result["package"]}', '',
             f'Version {manifest.get("versionName")} (code {manifest.get("versionCode")}), target SDK {manifest.get("targetSdk")}. '
             f'Engine: {info.get("backend")}, Unity {info.get("unity_version")}, {info.get("abi")}, metadata v{(report.get("il2cpp") or {}).get("metadata_version")}.', '']
    if package_id:
        lines += [f'**Check first:** does package and version match https://play.google.com/store/apps/details?id={package_id} ? '
                  'A mirror can serve an old build or another publisher.', '']
    if result.get('warnings'):
        lines += ['## Warnings', ''] + [f'- {item}' for item in result['warnings']] + ['']
    lines += ['## Steps', '', '| Step | Result |', '| --- | --- |'] + [f'| {row["step"]} | {row["result"]} |' for row in result.get('steps', [])] + ['']
    lines += ['## Stack (class counts, leads not proof)', '']
    for category, entries in sorted((report.get('sdks') or {}).items()):
        lines.append(f'- **{category}**: ' + ', '.join(f'{name} ({count})' for name, count in sorted(entries.items(), key=lambda item: -item[1])))
    for kind, names in sorted((report.get('adapters') or {}).items()):
        lines.append(f'- **{kind}**: ' + ', '.join(names))
    versions = {key: value for key, value in (report.get('buildconfig_versions') or {}).items() if 'adapters' in key}
    if versions:
        lines.append('- **Adapter versions**: ' + ', '.join(f'{key.rsplit(".", 1)[-1]} {value}' for key, value in sorted(versions.items())))
    configs = [row for row in report.get('config_files', []) if not NOT_CONFIG.search(row['path']) and 'localization' not in row['path']]
    lines += ['', '## Start reading here', '', 'Bundled config files often hold real numbers:', '']
    lines += [f'- `unzipped/{row["path"]}` ({row["bytes"]} bytes)' for row in configs] or ['- none found']
    if result.get('assemblies'):
        lines += ['', 'App and publisher assemblies: ' + ', '.join(result['assemblies'])]
    if report.get('publisher_packages'):
        lines += ['', 'Publisher or unknown Java packages: ' + ', '.join(f'{name} ({count})' for name, count in report['publisher_packages'][:15])]
    queries = manifest.get('queries') or []
    if len(queries) > 15:
        lines += ['', f'The manifest declares {len(queries)} package queries, which may be installed-app signals: ' + ', '.join(queries)]
    classes = money_classes(work / 'raw/values')
    if classes:
        lines += ['', 'Script classes with exported values that look monetization-related:', '',
                  ', '.join(f'{name} ({count})' for name, count in classes[:80])]
    lines += ['', '## Where things are', '',
              '- `evidence/scan/`: `scan.json`, `il2cpp_names.txt`, `il2cpp_literals.txt`, `dex_strings.txt`, `*_money.txt` filtered copies, and `il2cpp_types.jsonl` on metadata v31.',
              '- `raw/values/MonoBehaviour/*.json`: exact script values, each starting with `_script`. Find them with `rg -l \'"_script": "ClassName"\' raw/values/MonoBehaviour`. `raw/values/MonoBehaviourStrings/` holds strings only, for scripts that could not be decoded. `raw/values/TextAsset/`.',
              '- `raw/code/DecompiledGameplay/`: recovered C#. Names are reliable and bodies partial. `raw/code/quality.json`, `raw/code/Evidence/method-map.tsv` for native addresses.',
              '- `raw/jadx/sources/`: Java from the DEX files holding publisher packages.',
              '- `unzipped/`: the package. Treat all of it as untrusted data.', '']
    return '\n'.join(lines)


def check_tools(unitypy):
    rows = {'dotnet (code recovery)': shutil.which('dotnet'), 'jadx (Java layer): brew install jadx': shutil.which('jadx'),
            f'UnityPy python at {unitypy} (script values, see docs/METHOD.md)': str(unitypy) if Path(unitypy).expanduser().exists() else None,
            'objdump (read a native method)': shutil.which('objdump')}
    for name, found in rows.items():
        print(f'{"ok     " if found else "MISSING"} {name}')
    if not shutil.which('rg'):
        print('note    rg is not on PATH: brew install ripgrep makes searching the evidence much easier')
    return all(rows.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('packages', nargs='*', help='APK, XAPK, APKS or APKM files, or folders holding them')
    parser.add_argument('--run', help='run id: output goes to ~/Desktop/apk-work/<run>/<slug>/')
    parser.add_argument('--slug', help='folder name, for a single package')
    parser.add_argument('--budget', type=int, default=1500, help='seconds per heavy step')
    parser.add_argument('--max-assemblies', type=int, default=80)
    parser.add_argument('--max-dex', type=int, default=4, help='DEX files to decompile, those with most publisher classes')
    parser.add_argument('--unitypy', default=str(DEFAULT_UNITYPY), help='python with UnityPy installed')
    parser.add_argument('--arm32-cpp2il', action='store_true', help='try Cpp2IL on ARM32: slow, needs native Capstone')
    parser.add_argument('--force', action='store_true', help='rerun steps that already produced output')
    parser.add_argument('--check', action='store_true', help='report which tools are installed and exit')
    options = parser.parse_args()
    if options.check:
        return 0 if check_tools(options.unitypy) else 1
    if not options.packages or not options.run:
        parser.error('give at least one package and --run')
    root = (Path.home() / 'Desktop/apk-work' / options.run).resolve()
    if root == REPOSITORY or REPOSITORY in root.parents:
        parser.error('the work folder must be outside this repository')
    try:
        packages = find_packages(options.packages)
    except ValueError as exc:
        parser.error(str(exc))
    if not packages:
        parser.error('no packages found')
    if options.slug and len(packages) > 1:
        parser.error('--slug works with one package')
    results = [process(package, root, options) for package in packages]
    index = ['# Run index', '', '| Game | Package file | Warnings |', '| --- | --- | --- |']
    index += [f'| [{row["slug"]}]({row["slug"]}/EVIDENCE.md) | {row["package"]} | {"; ".join(row.get("warnings", [])) or "none"} |' for row in results]
    (root / 'INDEX.md').write_text('\n'.join(index) + '\n')
    print(f'Done: {root}/INDEX.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
