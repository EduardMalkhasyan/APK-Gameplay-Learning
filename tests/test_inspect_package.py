"""Synthetic container fixtures only; no recovered app code is executed."""
import io
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from toolkit.inspect_package import inspect_package


def archive_bytes(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return stream.getvalue()


class InventoryTests(unittest.TestCase):
    def inspect_bytes(self, payload, name='fixture.apk'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_bytes(payload)
            report = inspect_package(path)
            self.assertEqual(path.read_bytes(), payload)
            self.assertFalse(report['native_equivalence_verified'])
            return report

    def test_split_flutter_arm32_is_not_assumed_arm64(self):
        split = archive_bytes({'lib/armeabi-v7a/libflutter.so': b'',
                               'lib/armeabi-v7a/libapp.so': b''})
        report = self.inspect_bytes(archive_bytes({'config.apk': split}), 'fixture.xapk')
        self.assertEqual(report['architectures'], ['armeabi-v7a'])
        self.assertIn('flutter', report['runtime_signals'])
        self.assertIn('fixture.xapk!/config.apk', report['archives'])

    def test_mixed_runtimes_remain_visible(self):
        report = self.inspect_bytes(archive_bytes({
            'lib/arm64-v8a/libil2cpp.so': b'',
            'assets/global-metadata.dat': b'',
            'lib/arm64-v8a/libflutter.so': b''}))
        self.assertIn('unity_il2cpp', report['runtime_signals'])
        self.assertIn('flutter', report['runtime_signals'])

    def test_managed_assembly_signal(self):
        report = self.inspect_bytes(archive_bytes({'assets/bin/Data/Managed/Assembly-CSharp.dll': b''}))
        self.assertIn('unity_managed', report['runtime_signals'])

    def test_dex_does_not_imply_unity_or_gameplay(self):
        report = self.inspect_bytes(archive_bytes({'classes.dex': b'dex'}))
        self.assertTrue(report['payloads']['dex'])
        self.assertEqual(report['runtime_signals'], {})

    def test_elf_architecture_without_runtime_claim(self):
        header = bytearray(64)
        header[:6] = b'\x7fELF\x01\x01'
        struct.pack_into('<H', header, 18, 40)
        report = self.inspect_bytes(header, 'fixture.so')
        self.assertEqual(report['architectures'], ['ARM32'])
        self.assertEqual(report['elf_bits'], 32)
        self.assertEqual(report['runtime_signals'], {})

    def test_nested_filename_cannot_escape_workspace(self):
        payload = archive_bytes({'../outside.apk': archive_bytes({'classes.dex': b''})})
        report = self.inspect_bytes(payload, 'fixture.xapk')
        self.assertTrue(report['payloads']['dex'])

    def test_invalid_nested_split_is_reported(self):
        report = self.inspect_bytes(archive_bytes({'config.apk': b'not a zip'}))
        self.assertTrue(any('Invalid nested APK' in x for x in report['warnings']))


if __name__ == '__main__':
    unittest.main()
