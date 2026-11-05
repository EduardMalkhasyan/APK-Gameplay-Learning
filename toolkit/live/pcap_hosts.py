"""Standard library only. Hosts seen in a pcap: DNS questions, TLS SNI, and UDP/443 (QUIC) attempts by destination."""
import collections
import socket
import struct
import sys


def dns_name(data, offset):
    labels = []
    while offset < len(data):
        size = data[offset]
        if size == 0 or size & 0xC0:
            break
        labels.append(data[offset + 1:offset + 1 + size].decode('ascii', 'replace'))
        offset += 1 + size
    return '.'.join(labels)


def sni(payload):
    """The server name from a TLS ClientHello, or None."""
    try:
        if payload[0] != 22 or payload[5] != 1:
            return None
        pos = 43
        pos += 1 + payload[pos]
        pos += 2 + struct.unpack('>H', payload[pos:pos + 2])[0]
        pos += 1 + payload[pos]
        end = pos + 2 + struct.unpack('>H', payload[pos:pos + 2])[0]
        pos += 2
        while pos + 4 <= end:
            kind, size = struct.unpack('>HH', payload[pos:pos + 4])
            if kind == 0:
                length = struct.unpack('>H', payload[pos + 7:pos + 9])[0]
                return payload[pos + 9:pos + 9 + length].decode('ascii', 'replace')
            pos += 4 + size
    except (IndexError, struct.error):
        return None
    return None


def main(path):
    dns, names, quic, plain = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    with open(path, 'rb') as stream:
        header = stream.read(24)
        endian = '<' if header[:4] in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1') else '>'
        while True:
            record = stream.read(16)
            if len(record) < 16:
                break
            size = struct.unpack(endian + 'IIII', record)[2]
            frame = stream.read(size)
            if len(frame) < 34 or frame[12:14] != b'\x08\x00':
                continue
            ip = frame[14:]
            proto, head = ip[9], (ip[0] & 15) * 4
            dst = socket.inet_ntoa(ip[16:20])
            body = ip[head:]
            if proto == 17 and len(body) >= 8:
                port = struct.unpack('>H', body[2:4])[0]
                if port == 53:
                    name = dns_name(body[8:], 12)
                    if name:
                        dns[name] += 1
                elif port == 443:
                    quic[dst] += 1
            elif proto == 6 and len(body) >= 20:
                port = struct.unpack('>H', body[2:4])[0]
                payload = body[(body[12] >> 4) * 4:]
                if payload:
                    name = sni(payload)
                    if name:
                        names[name] += 1
                    if port == 80:
                        plain[dst] += 1
    print('DNS names', len(dns))
    print('TLS names', len(names))
    print('QUIC packets by destination', sum(quic.values()), quic.most_common(8))
    print('plain HTTP packets', sum(plain.values()), plain.most_common(5))
    for name, count in sorted((dns + names).items()):
        print(f'{count:6} {name}')


if __name__ == '__main__':
    main(sys.argv[1])
