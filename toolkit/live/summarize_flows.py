"""mitmproxy addon: what a captured session talked to, and the bodies worth reading.

mitmdump -n -q -r flows.mitm -s toolkit/live/summarize_flows.py --set out=<folder>

Writes <folder>/flows.json (one row per response) and saves request and response bodies of
monetization hosts to <folder>/bodies. Bodies can hold device ids and tokens: keep them in the
work folder and mask them in anything you write.
"""
import collections
import hashlib
import json
from pathlib import Path
import re

from mitmproxy import ctx

INTERESTING = re.compile(r'saygames|saykit|applovin|applvn|firebaseremoteconfig|firebaseinstallations|appsflyer|adjust|'
                         r'gameanalytics|graph\.facebook|supercent|playgendary|unity3d|ironsrc|levelplay', re.I)
rows = []
hosts = collections.Counter()


def load(loader):
    loader.add_option('out', str, '', 'output folder')


def request_host(flow):
    return flow.request.host_header or flow.request.pretty_host


def response(flow):
    host = request_host(flow).split(':')[0]
    hosts[host] += 1
    body = flow.response.content or b''
    sent = flow.request.content or b''
    row = {'t': round(flow.request.timestamp_start, 1), 'method': flow.request.method, 'host': host,
           'path': flow.request.path.split('?')[0][:120], 'status': flow.response.status_code,
           'sent': len(sent), 'got': len(body), 'type': flow.response.headers.get('content-type', '')[:40]}
    rows.append(row)
    if INTERESTING.search(host):
        out = Path(ctx.options.out) / 'bodies'
        out.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha1(f'{row["t"]}{host}{row["path"]}'.encode()).hexdigest()[:10]
        row['saved'] = name
        (out / f'{name}.req').write_bytes(sent)
        (out / f'{name}.res').write_bytes(body)


def done():
    out = Path(ctx.options.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'flows.json').write_text(json.dumps(rows, indent=0))
    groups = collections.defaultdict(lambda: [0, 0, 0])
    for row in rows:
        group = groups[(row['host'], row['method'], row['path'])]
        group[0] += 1
        group[1] += row['sent']
        group[2] += row['got']
    print(len(rows), 'responses,', len(hosts), 'hosts')
    for (host, method, path), (count, sent, got) in sorted(groups.items(), key=lambda item: (not INTERESTING.search(item[0][0]), -item[1][0]))[:60]:
        print(f'{count:4} {method:4} {host}{path[:60]}  sent {sent} got {got}')
