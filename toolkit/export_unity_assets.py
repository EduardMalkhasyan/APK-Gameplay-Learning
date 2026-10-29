"""Export a Unity game's sprites, textures, audio, meshes, fonts, text and script values with UnityPy.

Read-only on the input; writes only inside the output folder, which must be outside this repository.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import sys
import time

REPOSITORY = Path(__file__).resolve().parent.parent
SAFE_NAME = re.compile(r'[^\w.-]')


def safe_name(name, fallback):
    return SAFE_NAME.sub('_', name or fallback)[:80] or fallback


class Exporter:
    def __init__(self, out, deadline):
        self.out = out
        self.deadline = deadline
        self.counts = collections.Counter()
        self.failed = collections.Counter()

    def target(self, kind, name, path_id, ext):
        folder = self.out / kind
        folder.mkdir(parents=True, exist_ok=True)
        return folder / (safe_name(name, kind) + '_' + str(path_id) + ext)

    def save(self, kind, name, path_id, ext, data):
        self.target(kind, name, path_id, ext).write_bytes(data)
        self.counts[kind] += 1

    def over(self):
        return time.monotonic() > self.deadline


def type_tree_generator(env, objects, unzipped):
    try:
        from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
    except ImportError:
        return 'TypeTreeGeneratorAPI is not installed (pip install "UnityPy[full]")'
    version = next((o.assets_file.unity_version for o in objects if o.assets_file.unity_version not in ('', '0.0.0')), None)
    if version is None:
        return 'Unity version not found'
    managed = unzipped / 'assets/bin/Data/Managed'
    il2cpp = sorted(unzipped.glob('lib/arm64-v8a/libil2cpp.so')) + sorted(unzipped.glob('lib/*/libil2cpp.so'))
    metadata = managed / 'Metadata/global-metadata.dat'
    generator = TypeTreeGenerator(version)
    try:
        if il2cpp and metadata.exists():
            generator.load_il2cpp(il2cpp[0].read_bytes(), metadata.read_bytes())
        elif any(managed.glob('*.dll')):
            generator.load_local_dll_folder(str(managed))
        else:
            return 'no Managed DLLs or IL2CPP binary + metadata'
    except Exception as error:
        return 'type trees could not be generated for Unity %s: %s' % (version, error)
    env.typetree_generator = generator
    return None


def export(unzipped, out, max_meshes, budget):
    import UnityPy
    data = unzipped / 'assets'
    if data.is_dir() == False:
        raise RuntimeError('%s has no assets/ folder: unzip every split (and the OBB) into it first' % unzipped)
    env = UnityPy.load(str(data))
    objects = env.objects
    if len(objects) == 0:
        raise RuntimeError('no Unity objects found under %s' % data)
    exporter = Exporter(out, time.monotonic() + budget)
    notes = []
    print('%d Unity objects' % len(objects), flush=True)

    uses = collections.Counter()
    for obj in objects:
        if obj.type.name in ('MeshFilter', 'SkinnedMeshRenderer'):
            try:
                mesh = obj.read().m_Mesh.deref()
                uses[(mesh.assets_file.name, mesh.path_id)] += 1
            except Exception:
                continue
    if len(uses) == 0:
        uses.update((o.assets_file.name, o.path_id) for o in objects if o.type.name == 'Mesh')
    top_meshes = {key for key, _ in uses.most_common(max_meshes)}
    if len(uses) > max_meshes:
        notes.append('exported the %d most used of %d meshes' % (max_meshes, len(uses)))

    problem = type_tree_generator(env, objects, unzipped)
    values_note = problem

    for obj in objects:
        if exporter.over():
            notes.append('time budget of %d s reached: the rest was skipped' % budget)
            break
        kind = obj.type.name
        try:
            if kind in ('Sprite', 'Texture2D'):
                item = obj.read()
                item.image.save(exporter.target(kind, item.m_Name, obj.path_id, '.png'))
                exporter.counts[kind] += 1
            elif kind == 'AudioClip':
                clip = obj.read()
                for name, raw in clip.samples.items():
                    stem, ext = os.path.splitext(name)
                    exporter.save(kind, stem, obj.path_id, ext or '.wav', raw)
            elif kind == 'Mesh' and (obj.assets_file.name, obj.path_id) in top_meshes:
                mesh = obj.read()
                text = mesh.export()
                if text:
                    exporter.save(kind, mesh.m_Name, obj.path_id, '.obj', text.encode('utf-8', 'surrogateescape'))
            elif kind == 'TextAsset':
                item = obj.read()
                exporter.save(kind, item.m_Name, obj.path_id, '.txt', item.m_Script.encode('utf-8', 'surrogateescape'))
            elif kind == 'Font':
                item = obj.read()
                raw = bytes(item.m_FontData or b'')
                if raw:
                    exporter.save(kind, item.m_Name, obj.path_id, '.otf' if raw[:4] == b'OTTO' else '.ttf', raw)
            elif kind == 'MonoBehaviour':
                tree = obj.read_typetree()
                name = tree.get('m_Name') if isinstance(tree, dict) else None
                text = json.dumps(tree, indent=1, ensure_ascii=False, default=str)
                exporter.save(kind, name, obj.path_id, '.json', text.encode('utf-8', 'surrogateescape'))
        except Exception as error:
            exporter.failed[kind + ': ' + type(error).__name__] += 1
    if values_note and exporter.failed.get('MonoBehaviour: ValueError'):
        notes.append('script values unreadable: ' + values_note)
    return {'output': str(out), 'exported': dict(exporter.counts), 'failed': dict(exporter.failed), 'notes': notes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('unzipped', type=Path, help='folder with every split (and OBB) unzipped into it')
    parser.add_argument('output', type=Path, help='new folder outside this repository')
    parser.add_argument('--max-meshes', type=int, default=300)
    parser.add_argument('--budget', type=int, default=900, help='seconds before the export stops')
    args = parser.parse_args()
    out = args.output.expanduser().resolve()
    if out == REPOSITORY or REPOSITORY in out.parents:
        parser.exit(2, 'Asset export failed: the output must be outside this repository (use ~/apk-work/<run-id>/assets)\n')
    if out.exists() and any(out.iterdir()):
        parser.exit(2, 'Asset export failed: %s is not empty\n' % out)
    try:
        report = export(args.unzipped.expanduser().resolve(strict=True), out, args.max_meshes, args.budget)
    except ImportError:
        parser.exit(2, 'Asset export failed: UnityPy is not installed (see docs/METHOD.md)\n')
    except (OSError, RuntimeError) as error:
        parser.exit(2, 'Asset export failed: %s\n' % error)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
