"""Synthetic fixtures only: hand-built binary formats, no game files."""
from pathlib import Path
import struct
import tempfile
import unittest

from toolkit.scan_monetization import Dex, V31_SECTIONS, mask, parse_axml, read_il2cpp, read_il2cpp_types, read_manifest, scan


def string_pool(strings):
    data = b''
    offsets = []
    for text in strings:
        raw = text.encode('utf-8')
        offsets.append(len(data))
        data += bytes([len(text), len(raw)]) + raw + b'\0'
    data += b'\0' * (-len(data) % 4)
    header_size = 28
    strings_start = header_size + 4 * len(strings)
    size = strings_start + len(data)
    return struct.pack('<HHIIIIII', 1, header_size, size, len(strings), 0, 0x100, strings_start, 0) \
        + struct.pack(f'<{len(strings)}I', *offsets) + data


def attribute(key, raw, kind, value):
    return struct.pack('<IIIHxBI', 0xFFFFFFFF, key, raw, 8, kind, value)


def start_element(name, attributes):
    body = struct.pack('<IIHHHHHH', 0xFFFFFFFF, name, 20, 20, len(attributes), 0, 0, 0) + b''.join(attributes)
    return struct.pack('<HHIII', 0x0102, 16, 16 + len(body), 1, 0xFFFFFFFF) + body


def end_element(name):
    return struct.pack('<HHIIIII', 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, name)


def axml(strings, chunks):
    body = string_pool(strings) + b''.join(chunks)
    return struct.pack('<HHI', 3, 8, 8 + len(body)) + body


def manifest_bytes():
    strings = ['manifest', 'package', 'com.example.game', 'versionName', '1.2.3', 'versionCode',
               'uses-permission', 'name', 'android.permission.INTERNET', 'meta-data', 'value',
               'com.example.SDK_KEY', 'abcdefghijklmnop', 'queries', 'com.other.app', 'application']
    return axml(strings, [
        start_element(0, [attribute(1, 2, 3, 0), attribute(3, 4, 3, 0), attribute(5, 0xFFFFFFFF, 0x10, 42)]),
        start_element(6, [attribute(7, 8, 3, 0)]), end_element(6),
        start_element(13, []), start_element(1, [attribute(7, 14, 3, 0)]), end_element(1), end_element(13),
        start_element(15, []),
        start_element(9, [attribute(7, 11, 3, 0), attribute(10, 12, 3, 0)]), end_element(9),
        end_element(15), end_element(0)])


def dex_bytes(strings, classes):
    """A minimal DEX: strings, the types they name, and class_defs for `classes`."""
    header_size = 0x70
    string_ids_off = header_size
    type_ids_off = string_ids_off + 4 * len(strings)
    class_defs_off = type_ids_off + 4 * len(classes)
    data_off = class_defs_off + 32 * len(classes)
    data, offsets = b'', []
    for text in strings:
        offsets.append(data_off + len(data))
        raw = text.encode('utf-8')
        data += bytes([len(text)]) + raw + b'\0'
    header = bytearray(header_size)
    header[:8] = b'dex\n039\0'
    struct.pack_into('<4I', header, 0x38, len(strings), string_ids_off, len(classes), type_ids_off)
    struct.pack_into('<2I', header, 0x60, len(classes), class_defs_off)
    body = struct.pack(f'<{len(strings)}I', *offsets)
    body += struct.pack(f'<{len(classes)}I', *[strings.index(name) for name in classes])
    for index in range(len(classes)):
        body += struct.pack('<8I', index, 1, 0xFFFFFFFF, 0, 0xFFFFFFFF, 0, 0, 0)
    return bytes(header) + body + data


def metadata_v31(names, literals):
    data = b''.join(item.encode() for item in literals)
    table, position = b'', 0
    for item in literals:
        table += struct.pack('<II', len(item), position)
        position += len(item)
    identifiers = b'\0'.join(item.encode() for item in names) + b'\0'
    header = 8 + 6 * 4
    return struct.pack('<II6I', 0xFAB11BAF, 31, header, len(table), header + len(table), len(data),
                       header + len(table) + len(data), len(identifiers)) + table + data + identifiers


def metadata_v39(names, literals):
    data = b''.join(item.encode() for item in literals)
    starts, position = [], 0
    for item in literals:
        starts.append(position)
        position += len(item)
    table = struct.pack(f'<{len(starts)}I', *starts)
    identifiers = b'\0'.join(item.encode() for item in names) + b'\0'
    header = 8 + 9 * 4
    return struct.pack('<II9I', 0xFAB11BAF, 39, header, len(table), len(starts),
                       header + len(table), len(data), len(starts) - 1,
                       header + len(table) + len(data), len(identifiers), len(names)) + table + data + identifiers


def metadata_types_v31():
    names = b'\0Game.dll\0Shop\0Sale\0price\0Buy\0'
    offset = {'Game.dll': 1, 'Shop': 10, 'Sale': 15, 'price': 20, 'Buy': 26}
    sections = {name: b'' for name in V31_SECTIONS}
    sections['string'] = names
    sections['fields'] = struct.pack('<III', offset['price'], 0, 0)
    sections['methods'] = struct.pack('<9I', offset['Buy'], 0, 0, 0, 0, 0, 0, 0, 0)
    definition = bytearray(88)
    struct.pack_into('<II', definition, 0, offset['Shop'], offset['Sale'])
    struct.pack_into('<ii', definition, 32, 0, 0)
    struct.pack_into('<HHH', definition, 64, 1, 0, 1)
    sections['typeDefinitions'] = bytes(definition)
    sections['images'] = struct.pack('<4I', offset['Game.dll'], 0, 0, 1) + bytes(24)
    header = 8 + 8 * len(V31_SECTIONS)
    table, body = b'', b''
    for name in V31_SECTIONS:
        table += struct.pack('<II', header + len(body), len(sections[name]))
        body += sections[name]
    return struct.pack('<II', 0xFAB11BAF, 31) + table + body


class ManifestTests(unittest.TestCase):
    def test_reads_binary_manifest_and_masks_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'AndroidManifest.xml'
            path.write_bytes(manifest_bytes())
            report = read_manifest(path)
        self.assertEqual(report['package'], 'com.example.game')
        self.assertEqual(report['versionName'], '1.2.3')
        self.assertEqual(report['versionCode'], 42)
        self.assertEqual(report['permissions'], ['android.permission.INTERNET'])
        self.assertEqual(report['queries'], ['com.other.app'])
        self.assertEqual(report['metadata']['com.example.SDK_KEY'], 'ab...op')

    def test_rejects_text_xml(self):
        with self.assertRaises(ValueError):
            list(parse_axml(b'<manifest></manifest>'))

    def test_mask_keeps_plain_values(self):
        self.assertEqual(mask('com.example.mode', 'production-value'), 'production-value')
        self.assertEqual(mask('com.example.api_key', 'short'), 'short')


class DexTests(unittest.TestCase):
    def test_lists_defined_classes(self):
        dex = Dex(dex_bytes(['Lcom/applovin/sdk/AppLovinSdk;', 'hello'], ['Lcom/applovin/sdk/AppLovinSdk;']))
        self.assertEqual(list(dex.class_names()), ['com/applovin/sdk/AppLovinSdk'])
        self.assertIn('hello', list(dex.strings()))

    def test_rejects_other_files(self):
        with self.assertRaises(ValueError):
            Dex(b'not a dex file at all')


class MetadataTests(unittest.TestCase):
    def read(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'global-metadata.dat'
            path.write_bytes(payload)
            return read_il2cpp(path)

    def test_version_31(self):
        version, names, literals = self.read(metadata_v31(['AdsManager', 'Offer'], ['no_ads', 'rewarded']))
        self.assertEqual(version, 31)
        self.assertEqual(names, ['AdsManager', 'Offer'])
        self.assertEqual(literals, ['no_ads', 'rewarded'])

    def test_version_39_literals_have_no_lengths(self):
        version, names, literals = self.read(metadata_v39(['AdsManager'], ['no_ads', 'rewarded']))
        self.assertEqual(version, 39)
        self.assertEqual(names, ['AdsManager'])
        self.assertEqual(literals, ['no_ads', 'rewarded'])

    def test_type_listing_needs_no_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'global-metadata.dat'
            path.write_bytes(metadata_types_v31())
            rows = list(read_il2cpp_types(path))
        self.assertEqual(rows, [{'asm': 'Game.dll', 'type': 'Sale.Shop', 'fields': ['price'], 'methods': ['Buy']}])

    def test_protected_metadata_is_refused(self):
        with self.assertRaises(ValueError):
            self.read(struct.pack('<II', 0x12345678, 31) + b'\0' * 64)


class ScanTests(unittest.TestCase):
    def test_finds_sdks_and_adapters(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'unzipped'
            root.mkdir()
            (root / 'AndroidManifest.xml').write_bytes(manifest_bytes())
            (root / 'billing.properties').write_text('version=8.3.0\n')
            classes = ['Lcom/applovin/sdk/AppLovinSdk;', 'Lcom/applovin/mediation/adapters/MoloMediationAdapter;',
                       'Lcom/android/billingclient/api/BillingClient;']
            (root / 'classes.dex').write_bytes(dex_bytes(classes + ['https://example.test/x'], classes))
            report = scan(root, Path(folder) / 'out')
            self.assertIn('AppLovin MAX', report['sdks']['mediation'])
            self.assertIn('Google Play Billing', report['sdks']['purchase'])
            self.assertEqual(report['adapters']['MAX adapter'], ['Molo'])
            self.assertEqual(report['versions']['billing'], '8.3.0')
            self.assertEqual(report['endpoints'], ['https://example.test'])
            self.assertTrue((Path(folder) / 'out' / 'scan.json').exists())

    def test_refuses_output_inside_repository(self):
        repository = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                scan(folder, repository / 'runs' / 'scan')


if __name__ == '__main__':
    unittest.main()
