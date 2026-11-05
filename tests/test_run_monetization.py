"""Synthetic fixtures only: pure helpers, no game files and no heavy tools."""
import json
from pathlib import Path
import tempfile
import unittest

import sys

from toolkit.run_monetization import (Steps, app_assemblies, build_warnings, describe, evidence_page, find_packages,
                                      money_classes, slug_from_filename)


class SlugTests(unittest.TestCase):
    def test_mirror_file_names(self):
        self.assertEqual(slug_from_filename('Some+Game!_31.8.0_APKPure.xapk'), 'some-game')
        self.assertEqual(slug_from_filename('My+Other+Game_1.39.0_APKPure.xapk'), 'my-other-game')
        self.assertEqual(slug_from_filename('game.apk'), 'game')

    def test_never_empty(self):
        self.assertEqual(slug_from_filename('!!!.apk'), 'package')


class PackageTests(unittest.TestCase):
    def test_folder_lists_packages_only(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('b.xapk', 'a.apk', 'notes.md'):
                (Path(folder) / name).write_bytes(b'')
            self.assertEqual([path.name for path in find_packages([folder])], ['a.apk', 'b.xapk'])

    def test_other_files_are_refused(self):
        with self.assertRaises(ValueError):
            find_packages(['notes.md'])


class AssemblyTests(unittest.TestCase):
    def test_keeps_game_and_publisher_code(self):
        names = ['System.Core.dll', 'UnityEngine.UI.dll', 'PublisherKit.Internal.dll', 'Firebase.App.dll', 'Assembly-CSharp.dll', 'GameCore.dll']
        self.assertEqual(app_assemblies(names), ['Assembly-CSharp', 'GameCore', 'PublisherKit.Internal'])

    def test_limit(self):
        self.assertEqual(len(app_assemblies([f'Game{index}.dll' for index in range(9)], limit=3)), 3)


class DescribeTests(unittest.TestCase):
    def build(self, abi=None, metadata=True, version=b'6000.0.62f1'):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        data = root / 'assets/bin/Data'
        (data / 'Managed/Metadata').mkdir(parents=True)
        (data / 'data.unity3d').write_bytes(b'UnityFS\0' + version + b'\0')
        (data / 'ScriptingAssemblies.json').write_text(json.dumps({'names': ['Assembly-CSharp.dll']}))
        if metadata:
            (data / 'Managed/Metadata/global-metadata.dat').write_bytes(b'x')
        if abi:
            (root / 'lib' / abi).mkdir(parents=True)
            (root / 'lib' / abi / 'libil2cpp.so').write_bytes(b'x')
        return root

    def test_prefers_arm64(self):
        root = self.build('arm64-v8a')
        (root / 'lib/armeabi-v7a').mkdir(parents=True)
        (root / 'lib/armeabi-v7a/libil2cpp.so').write_bytes(b'x')
        info = describe(root)
        self.assertEqual((info['backend'], info['abi'], info['unity_version']), ('il2cpp', 'arm64-v8a', '6000.0.62f1'))
        self.assertEqual(info['assemblies'], ['Assembly-CSharp.dll'])

    def test_library_without_metadata_is_not_il2cpp(self):
        self.assertEqual(describe(self.build('arm64-v8a', metadata=False))['backend'], 'not Unity')


class WarningTests(unittest.TestCase):
    def test_flags_an_old_build(self):
        info = {'backend': 'il2cpp', 'abi': 'armeabi-v7a'}
        warnings = build_warnings({'targetSdk': 29}, {'mediation': {'MoPub (legacy)': 10}}, info)
        self.assertEqual(len(warnings), 3)
        self.assertIn('MoPub', warnings[0])

    def test_quiet_on_a_current_build(self):
        info = {'backend': 'il2cpp', 'abi': 'arm64-v8a'}
        self.assertEqual(build_warnings({'targetSdk': 36}, {'mediation': {'AppLovin MAX': 10}}, info), [])


class ResumeTests(unittest.TestCase):
    MAKE = "import pathlib,sys; d=pathlib.Path(sys.argv[1]); d.mkdir(exist_ok=True); (d/'x').write_text('done'); sys.exit(int(sys.argv[2]))"

    def step(self, folder, code):
        steps = Steps(force=False)
        out = Path(folder) / 'out'
        passed = steps.run('demo', [sys.executable, '-I', '-c', self.MAKE, out, code], Path(folder) / 'demo.log', 30, output=out)
        return passed, steps.rows[0]['result']

    def test_failed_output_is_rebuilt_and_good_output_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            passed, result = self.step(folder, 3)
            self.assertFalse(passed)
            self.assertTrue((Path(folder) / 'out/x').exists())
            self.assertTrue((Path(folder) / 'demo.log.failed').exists())
            passed, result = self.step(folder, 0)
            self.assertTrue(passed)
            self.assertIn('exit 0', result)
            self.assertFalse((Path(folder) / 'demo.log.failed').exists())
            passed, result = self.step(folder, 3)
            self.assertTrue(passed)
            self.assertEqual(result, 'kept existing output')

    def test_timeout_is_a_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            steps = Steps(force=False)
            passed = steps.run('slow', [sys.executable, '-I', '-c', 'import time; time.sleep(5)'], Path(folder) / 'slow.log', 0.2)
            self.assertFalse(passed)
            self.assertIn('budget', steps.rows[0]['result'])


class EvidenceTests(unittest.TestCase):
    def test_money_classes_are_found_and_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            values = Path(folder) / 'MonoBehaviour'
            values.mkdir()
            (values / 'a_1.json').write_text('{"_script": "SpecialOfferProduct"}')
            (values / 'b_2.json').write_text('{"_script": "SpecialOfferProduct"}')
            (values / 'c_3.json').write_text('{"_script": "EnemySpawner"}')
            self.assertEqual(money_classes(Path(folder)), [('SpecialOfferProduct', 2)])

    def test_page_shows_warnings_and_where_to_start(self):
        report = {'manifest': {'package': 'com.example.game', 'versionName': '1.0'},
                  'sdks': {'mediation': {'AppLovin MAX': 10}},
                  'config_files': [{'path': 'assets/sdk_config.json', 'bytes': 900}, {'path': 'assets/mraid.js.txt', 'bytes': 9}]}
        result = {'package': 'game.apk', 'info': {'backend': 'il2cpp'}, 'steps': [{'step': 'scan', 'result': 'ok'}],
                  'warnings': ['Old build']}
        with tempfile.TemporaryDirectory() as folder:
            page = evidence_page(Path(folder), result, report)
        self.assertIn('Old build', page)
        self.assertIn('assets/sdk_config.json', page)
        self.assertNotIn('mraid', page)
        self.assertIn('id=com.example.game', page)


if __name__ == '__main__':
    unittest.main()
