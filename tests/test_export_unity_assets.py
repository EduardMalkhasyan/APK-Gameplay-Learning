"""Synthetic UnityPy stand-ins only; no game file is read."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

from toolkit import export_unity_assets


class File:
    name = 'sharedassets0.assets'
    unity_version = '2022.3.0f1'


class Kind:
    def __init__(self, name):
        self.name = name


class Image:
    def save(self, path):
        Path(path).write_bytes(b'png')


class Reader:
    def __init__(self, kind, path_id, item=None, tree=None, error=None):
        self.type = Kind(kind)
        self.path_id = path_id
        self.assets_file = File()
        self.item = item
        self.tree = tree
        self.error = error

    def read(self):
        if self.error:
            raise self.error
        return self.item

    def read_typetree(self):
        if self.error:
            raise self.error
        return self.tree


def item(**fields):
    return types.SimpleNamespace(**fields)


def fake_unitypy(objects):
    module = types.ModuleType('UnityPy')
    module.load = lambda path: types.SimpleNamespace(objects=objects)
    return module


class ExportTests(unittest.TestCase):
    def run_export(self, objects, max_meshes=300):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        unzipped = Path(directory.name) / 'unzipped'
        (unzipped / 'assets').mkdir(parents=True)
        out = Path(directory.name) / 'out'
        with mock.patch.dict(sys.modules, {'UnityPy': fake_unitypy(objects)}):
            report = export_unity_assets.export(unzipped, out, max_meshes, 60)
        return out, report

    def test_names_from_the_package_never_leave_the_output_folder(self):
        sprite = Reader('Sprite', 7, item(m_Name='../../escape', image=Image()))
        out, report = self.run_export([sprite])
        self.assertEqual(report['exported'], {'Sprite': 1})
        self.assertTrue((out / 'Sprite' / '.._.._escape_7.png').exists())
        self.assertEqual([p for p in out.parent.iterdir() if p.name.startswith('escape')], [])

    def test_audio_keeps_its_real_format_and_binary_text_does_not_crash(self):
        clip = Reader('AudioClip', 1, item(samples={'music.ogg': b'OggS'}))
        text = Reader('TextAsset', 2, item(m_Name='level', m_Script='\udc89binary'))
        out, report = self.run_export([clip, text])
        self.assertTrue((out / 'AudioClip' / 'music_1.ogg').exists())
        self.assertEqual((out / 'TextAsset' / 'level_2.txt').read_bytes(), b'\x89binary')
        self.assertEqual(report['failed'], {})

    def test_only_the_most_used_meshes_are_exported(self):
        used = Reader('Mesh', 10, item(m_Name='Hero', export=lambda: 'v 0 0 0\n'))
        unused = Reader('Mesh', 11, item(m_Name='Rock', export=lambda: 'v 1 1 1\n'))
        holder = Reader('MeshFilter', 12, item(m_Mesh=item(deref=lambda: used)))
        out, report = self.run_export([used, unused, holder], max_meshes=1)
        self.assertEqual(sorted(p.name for p in (out / 'Mesh').iterdir()), ['Hero_10.obj'])
        self.assertEqual(report['exported'], {'Mesh': 1})

    def test_one_broken_object_does_not_stop_the_export(self):
        broken = Reader('Texture2D', 3, error=FileNotFoundError('Resource file x.resS not found'))
        font = Reader('Font', 4, item(m_Name='Title', m_FontData=list(b'OTTOfont')))
        out, report = self.run_export([broken, font])
        self.assertEqual(report['failed'], {'Texture2D: FileNotFoundError': 1})
        self.assertTrue((out / 'Font' / 'Title_4.otf').exists())

    def test_only_the_current_file_keeps_its_decoded_images(self):
        first, second = File(), File()
        first._cache, second._cache = {1: 'atlas'}, {1: 'atlas'}
        a = Reader('Sprite', 1, item(m_Name='a', image=Image()))
        b = Reader('Sprite', 2, item(m_Name='b', image=Image()))
        a.assets_file, b.assets_file = first, second
        out, report = self.run_export([a, b])
        self.assertEqual(report['exported'], {'Sprite': 2})
        self.assertEqual(first._cache, {})
        self.assertEqual(second._cache, {1: 'atlas'})

    def test_output_inside_the_repository_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            argv = ['export_unity_assets.py', directory, str(export_unity_assets.REPOSITORY / 'work' / 'assets')]
            with mock.patch.object(sys, 'argv', argv), self.assertRaises(SystemExit) as stop:
                export_unity_assets.main()
        self.assertEqual(stop.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
