"""Synthetic bytes only: no captured traffic."""
import struct
import unittest

from toolkit.live.diff_json import diff, mask
from toolkit.live.pcap_hosts import dns_name, sni


def client_hello(name):
    host = name.encode()
    server_name = struct.pack('>BH', 0, len(host)) + host
    extension = struct.pack('>HHH', 0, len(server_name) + 2, len(server_name)) + server_name
    body = b'\x03\x03' + b'\x00' * 32 + b'\x00' + b'\x00\x02\x13\x01' + b'\x01\x00' + struct.pack('>H', len(extension)) + extension
    handshake = b'\x01' + len(body).to_bytes(3, 'big') + body
    return b'\x16\x03\x01' + struct.pack('>H', len(handshake)) + handshake


class PcapTests(unittest.TestCase):
    def test_server_name_from_client_hello(self):
        self.assertEqual(sni(client_hello('config.example.com')), 'config.example.com')

    def test_other_records_have_no_name(self):
        self.assertIsNone(sni(b'\x17\x03\x03\x00\x05hello'))

    def test_dns_question(self):
        self.assertEqual(dns_name(b'\x03api\x07example\x03com\x00', 0), 'api.example.com')


class DiffTests(unittest.TestCase):
    def test_nested_and_embedded_json(self):
        old = {'ads': {'gap': 120}, 'game': '{"Enabled": false}', 'list': [1, 2]}
        new = {'ads': {'gap': 180}, 'game': '{"Enabled": true}', 'list': [1, 2], 'added': 1}
        self.assertEqual(sorted(diff(old, new)), [('/added', None, 1), ('/ads/gap', 120, 180), ('/game/Enabled', False, True)])

    def test_ids_are_masked(self):
        self.assertEqual(mask('unit 0123456789abcdef'), 'unit 012...')


if __name__ == '__main__':
    unittest.main()
