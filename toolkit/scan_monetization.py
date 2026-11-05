"""Static monetization scan of an unpacked Android game. Signals are leads, never proof.

Reads AndroidManifest.xml, every classes*.dex, root .properties/.version files and an
IL2CPP global-metadata.dat. It writes the ad, attribution, analytics, purchase and
protection stack with versions, plus searchable name and string lists. Nothing from the
package is executed. Masks anything that looks like a key. Standard library only.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys

REPOSITORY = Path(__file__).resolve().parent.parent

SDKS = [
    # category, display name, class-path prefixes
    ('mediation', 'AppLovin MAX', ['com/applovin/mediation', 'com/applovin/sdk']),
    ('mediation', 'ironSource / Unity LevelPlay', ['com/ironsource/mediationsdk', 'com/unity3d/mediation']),
    ('mediation', 'Google AdMob / GAM', ['com/google/android/gms/ads']),
    ('mediation', 'Appodeal', ['com/appodeal/ads', 'com/appodeal/consent', 'com/explorestack']),
    ('mediation', 'BidMachine', ['io/bidmachine']),
    ('mediation', 'Bidon', ['org/bidon']),
    ('mediation', 'TradPlus', ['com/tradplus']),
    ('mediation', 'TopOn', ['com/anythink']),
    ('mediation', 'Yandex Mobile Ads', ['com/yandex/mobile/ads']),
    ('mediation', 'MoPub (legacy)', ['com/mopub']),
    ('mediation', 'Fyber FairBid', ['com/fyber/fairbid']),
    ('network', 'Unity Ads', ['com/unity3d/ads', 'com/unity3d/services']),
    ('network', 'Meta Audience Network', ['com/facebook/ads']),
    ('network', 'Mintegral', ['com/mbridge', 'com/mintegral']),
    ('network', 'Pangle', ['com/bytedance/sdk/openadsdk', 'com/pgl/']),
    ('network', 'Vungle / Liftoff', ['com/vungle']),
    ('network', 'InMobi', ['com/inmobi']),
    ('network', 'Moloco', ['com/moloco']),
    ('network', 'PubMatic / OpenWrap', ['com/pubmatic']),
    ('network', 'Smaato', ['com/smaato']),
    ('network', 'Verve / PubNative', ['net/pubnative']),
    ('network', 'HyprMX', ['com/hyprmx']),
    ('network', 'MobileFuse', ['com/mobilefuse']),
    ('network', 'Ogury', ['com/ogury']),
    ('network', 'Chartboost', ['com/chartboost']),
    ('network', 'Digital Turbine / DT Exchange', ['com/fyber/inneractive', 'com/digitalturbine']),
    ('network', 'Amazon APS', ['com/amazon/device/ads', 'com/amazon/aps']),
    ('network', 'BIGO Ads', ['sg/bigo/ads']),
    ('network', 'Kidoz', ['com/kidoz']),
    ('network', 'Maticoo / Zmaticoo', ['com/maticoo', 'com/zmaticoo']),
    ('network', 'Tapjoy', ['com/tapjoy']),
    ('network', 'AdColony', ['com/adcolony']),
    ('network', 'Criteo', ['com/criteo']),
    ('network', 'Start.io', ['com/startapp']),
    ('network', 'TaurusX', ['com/taurusx']),
    ('network', 'Nefta', ['com/nefta']),
    ('network', 'Anzu in-game ads', ['com/anzu']),
    ('network', 'Adverty in-game ads', ['com/adverty']),
    ('network', 'Gadsme in-game ads', ['com/gadsme']),
    ('attribution', 'Adjust', ['com/adjust/sdk']),
    ('attribution', 'AppsFlyer', ['com/appsflyer']),
    ('attribution', 'Singular', ['com/singular']),
    ('attribution', 'Kochava', ['com/kochava']),
    ('attribution', 'Tenjin', ['com/tenjin']),
    ('attribution', 'Airbridge', ['co/ab180']),
    ('attribution', 'Branch', ['io/branch']),
    ('analytics', 'Firebase Analytics', ['com/google/firebase/analytics', 'com/google/android/gms/measurement']),
    ('analytics', 'GameAnalytics', ['com/gameanalytics']),
    ('analytics', 'Amplitude', ['com/amplitude']),
    ('analytics', 'Mixpanel', ['com/mixpanel']),
    ('analytics', 'devtodev', ['com/devtodev']),
    ('analytics', 'ByteBrew', ['com/bytebrew']),
    ('analytics', 'Flurry', ['com/flurry']),
    ('analytics', 'ThinkingData', ['cn/thinkingdata', 'com/thinkingdata']),
    ('analytics', 'AppMetrica', ['com/yandex/metrica', 'io/appmetrica']),
    ('analytics', 'Facebook SDK', ['com/facebook/appevents']),
    ('analytics', 'Sentry', ['io/sentry']),
    ('analytics', 'Crashlytics', ['com/google/firebase/crashlytics']),
    ('purchase', 'Google Play Billing', ['com/android/billingclient']),
    ('purchase', 'Unity IAP', ['com/unity/purchasing']),
    ('purchase', 'RevenueCat', ['com/revenuecat']),
    ('purchase', 'Adapty', ['com/adapty']),
    ('purchase', 'Qonversion', ['com/qonversion']),
    ('purchase', 'Xsolla', ['com/xsolla']),
    ('consent', 'Google UMP', ['com/google/android/ump']),
    ('consent', 'Usercentrics', ['com/usercentrics']),
    ('consent', 'Didomi', ['io/didomi']),
    ('consent', 'OneTrust', ['com/onetrust']),
    ('consent', 'Sourcepoint', ['com/sourcepoint']),
    ('ad_quality', 'AppHarbr / GeoEdge', ['com/appharbr', 'com/geoedge']),
    ('ad_quality', 'SafeDK / Ad Review', ['com/safedk']),
    ('ad_quality', 'IAS', ['com/integralads']),
    ('config', 'Firebase Remote Config', ['com/google/firebase/remoteconfig']),
    ('config', 'Firebase A/B Testing', ['com/google/firebase/abt']),
    ('push', 'Firebase Messaging', ['com/google/firebase/messaging']),
    ('push', 'OneSignal', ['com/onesignal']),
    ('protection', 'Play Integrity', ['com/google/android/play/core/integrity', 'com/google/android/play/integrity']),
    ('protection', 'PairIP', ['com/pairip']),
    ('protection', 'Play Licensing', ['com/google/android/vending/licensing']),
    ('publisher', 'SayKit (SayGames)', ['saygames/', 'by/saygames', 'com/saygames']),
    ('publisher', 'Playgendary', ['com/playgendary']),
    ('publisher', 'Miniclip', ['com/miniclip']),
    ('mediation', 'Tapdaq (legacy)', ['com/tapdaq']),
    ('publisher', 'Supercent', ['io/supercent', 'com/supercent']),
    ('ml', 'TensorFlow Lite', ['org/tensorflow/lite', 'com/google/android/gms/tflite']),
]

ADAPTER_ROOTS = {
    'MAX adapter': re.compile(r'^com/applovin/mediation/adapters/(\w+?)MediationAdapter$'),
    'LevelPlay adapter': re.compile(r'^com/ironsource/adapters/(\w+)/\w+Adapter$'),
    'AdMob adapter': re.compile(r'^com/google/ads/mediation/(\w+)/\w+(?:Adapter|Mediation\w*)$'),
    'Appodeal adapter': re.compile(r'^com/appodeal/ads/adapters/(\w+)/\w*Network$'),
    'BidMachine network': re.compile(r'^io/bidmachine/.*?networks?/(\w+)/\w+Adapter$'),
    'Bidon adapter': re.compile(r'^org/bidon/(\w+)/\w+Adapter$'),
}

MONEY_WORDS = re.compile(
    r'(?i)(iap|in_?app|purchas|product|sku|offer|starter|no_?ads?\b|remove_?ads|noads|premium|vip|subscri|'
    r'battle_?pass|season_?pass|piggy|interstitial|rewarded|reward_?video|banner|mrec|app_?open|'
    r'ad_?(unit|placement|config|freq|cool|cap|pacing|manager|service|controller|interval|delay|break)|'
    r'bid_?floor|floor|ecpm|\bcpm|ltv|arpu|arpdau|payer|whale|dolphin|minnow|cohort|segment|'
    r'ab_?test|experiment|remote_?config|capping|pacing|grace|revive|second_?chance|double_?reward|'
    r'wallet|shop|store|gems?\b|diamond|currency|waterfall|mediation|postbid|prebid|adrevenue|ad_?revenue|'
    r'impression|pass_?reward|paywall|bundle_?offer|flash_?sale|limited_?time|daily_?deal)')
SECRET_NAMES = re.compile(r'(?i)(key|token|secret|app_?id|appid|application_?id|client_?id|sdk|dsn|auth)')
URL = re.compile(r'https?://[\w.\-]+')
# Java packages that are not a game's or publisher's own, beyond the SDK table above.
VENDOR_PREFIXES = ('android/', 'androidx/', 'kotlin', 'java/', 'javax/', 'dalvik/', 'okhttp3/', 'okio/', 'org/', 'retrofit2/',
                   'dagger/', 'coil/', 'bolts/', 'rx/', 'com/google/', 'com/android/', 'com/squareup/', 'com/fasterxml/',
                   'com/iab/', 'com/bumptech/', 'com/caverock/', 'com/explorestack/', 'com/my/', 'com/bykv/', 'com/apm/',
                   'com/tiktok/', 'com/iabtcf/', 'com/moat/', 'io/ktor/', 'io/grpc/', 'io/reactivex/', 'io/presage/',
                   'com/five_corp/', 'com/verve/', 'com/monetization/', 'com/auth0/', 'com/ysocorp/', 'com/applovin/',
                   'com/yandex/', 'com/ironsource/', 'com/zmaticoo/', 'com/taurusx/', 'com/fyber/', 'com/unity3d/',
                   'com/bytedance/', 'com/facebook/', 'com/appodeal/', 'com/pgl/', 'com/abovevacant/', 'com/tradplus/',
                   'com/kwad/', 'com/sigmob/', 'com/huawei/', 'com/digitalturbine/', 'com/superawesome/', 'tv/superawesome/',
                   'com/line/', 'jp/line/', 'com/linecorp/', 'com/gameanalytics/', 'com/bytebrew/', 'com/anzu/', 'com/hyprmx/',
                   'mozilla/', 'net/', 'sun/', 'lib/', 'de/', 'ch/', 'io/appmetrica/', 'io/sentry/', 'io/flutter/', 'javax/')
MAX_NAME = 300


def mask(name, value):
    text = str(value)
    if SECRET_NAMES.search(name) and len(text) >= 10:
        return text[:2] + '...' + text[-2:]
    return text


# Binary AndroidManifest.xml -------------------------------------------------

def read_pool(data, start):
    count, _, flags, strings_start, _ = struct.unpack_from('<5I', data, start + 8)
    offsets = struct.unpack_from(f'<{count}I', data, start + 28)
    base = start + strings_start
    utf8 = bool(flags & 0x100)
    pool = []
    for offset in offsets:
        position = base + offset
        if utf8:
            position += 2 if data[position] & 0x80 else 1
            length = data[position]
            position += 1
            if length & 0x80:
                length = ((length & 0x7F) << 8) | data[position]
                position += 1
            pool.append(data[position:position + length].decode('utf-8', 'replace'))
        else:
            length = struct.unpack_from('<H', data, position)[0]
            position += 2
            if length & 0x8000:
                length = ((length & 0x7FFF) << 16) | struct.unpack_from('<H', data, position)[0]
                position += 2
            pool.append(data[position:position + length * 2].decode('utf-16-le', 'replace'))
    return pool


# Attribute names can be stripped from the pool; the resource ids stay.
ATTRIBUTE_IDS = {0x01010003: 'name', 0x0101021b: 'versionCode', 0x0101021c: 'versionName',
                 0x0101020c: 'minSdkVersion', 0x01010270: 'targetSdkVersion', 0x01010024: 'value',
                 0x01010025: 'resource', 0x01010018: 'authorities'}


def parse_axml(data):
    """Yields (depth, tag, attributes) for each start element of a binary XML file."""
    if len(data) < 8 or struct.unpack_from('<H', data, 0)[0] != 3:
        raise ValueError('Not a binary XML file')
    pool, resources, position, depth = [], [], 8, 0
    while position + 8 <= len(data):
        kind, _, size = struct.unpack_from('<HHI', data, position)
        if size < 8:
            break
        if kind == 0x0001:
            pool = read_pool(data, position)
        elif kind == 0x0180:
            resources = list(struct.unpack_from(f'<{(size - 8) // 4}I', data, position + 8))
        elif kind == 0x0102:
            name_index = struct.unpack_from('<I', data, position + 20)[0]
            attr_start, attr_size, attr_count = struct.unpack_from('<HHH', data, position + 24)
            attributes = {}
            for index in range(attr_count):
                base = position + 16 + attr_start + index * attr_size
                _, key, raw, _, kind_byte, value = struct.unpack_from('<IIIHxBI', data, base + 0)
                label = pool[key] if key < len(pool) and pool[key] else ''
                if key < len(resources) and resources[key] in ATTRIBUTE_IDS:
                    label = ATTRIBUTE_IDS[resources[key]]
                if raw != 0xFFFFFFFF and raw < len(pool):
                    attributes[label] = pool[raw]
                elif kind_byte == 0x12:
                    attributes[label] = bool(value)
                elif kind_byte in (0x10, 0x11):
                    attributes[label] = struct.unpack('<i', struct.pack('<I', value))[0]
                else:
                    attributes[label] = f'@0x{value:08x}'
            yield depth, pool[name_index], attributes
            depth += 1
        elif kind == 0x0103:
            depth -= 1
        position += size


def read_manifest(path):
    report = {'package': None, 'versionName': None, 'versionCode': None, 'minSdk': None, 'targetSdk': None,
              'permissions': [], 'metadata': {}, 'activities': [], 'services': [], 'receivers': [],
              'providers': [], 'queries': []}
    in_queries = None
    for depth, tag, attributes in parse_axml(path.read_bytes()):
        if in_queries is not None and depth <= in_queries:
            in_queries = None
        if tag == 'manifest':
            report['package'] = attributes.get('package')
            report['versionName'] = attributes.get('versionName')
            report['versionCode'] = attributes.get('versionCode')
        elif tag == 'uses-sdk':
            report['minSdk'] = attributes.get('minSdkVersion')
            report['targetSdk'] = attributes.get('targetSdkVersion')
        elif tag in ('uses-permission', 'uses-permission-sdk-23'):
            report['permissions'].append(attributes.get('name'))
        elif tag == 'meta-data' and 'name' in attributes:
            value = attributes.get('value', attributes.get('resource'))
            report['metadata'][attributes['name']] = mask(attributes['name'], value)
        elif tag in ('activity', 'activity-alias'):
            report['activities'].append(attributes.get('name'))
        elif tag == 'service':
            report['services'].append(attributes.get('name'))
        elif tag == 'receiver':
            report['receivers'].append(attributes.get('name'))
        elif tag == 'provider':
            report['providers'].append(attributes.get('name'))
        elif tag == 'queries':
            in_queries = depth
        elif in_queries is not None and tag == 'package':
            report['queries'].append(attributes.get('name'))
    return report


# DEX ------------------------------------------------------------------------

def uleb(data, position):
    result = shift = 0
    while True:
        byte = data[position]
        position += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, position
        shift += 7


def read_dex_string(data, offset):
    _, position = uleb(data, offset)
    end = data.index(b'\0', position)
    return data[position:end].decode('utf-8', 'replace')


class Dex:
    def __init__(self, data):
        if data[:3] != b'dex':
            raise ValueError('Not a DEX file')
        self.data = data
        self.string_count, self.string_off, self.type_count, self.type_off = struct.unpack_from('<4I', data, 0x38)
        self.field_count, self.field_off = struct.unpack_from('<2I', data, 0x50)
        self.class_count, self.class_off = struct.unpack_from('<2I', data, 0x60)

    def string(self, index):
        offset = struct.unpack_from('<I', self.data, self.string_off + index * 4)[0]
        return read_dex_string(self.data, offset)

    def strings(self):
        for index in range(self.string_count):
            yield self.string(index)

    def type_name(self, index):
        descriptor = struct.unpack_from('<I', self.data, self.type_off + index * 4)[0]
        return self.string(descriptor)

    def classes(self):
        for index in range(self.class_count):
            yield struct.unpack_from('<8I', self.data, self.class_off + index * 32)

    def class_names(self):
        for row in self.classes():
            yield self.type_name(row[0])[1:-1]

    def static_strings(self, row):
        """String constants in a class's static initial values, keyed by field name."""
        class_data, static_values = row[6], row[7]
        if not class_data or not static_values:
            return {}
        data = self.data
        statics, position = uleb(data, class_data)
        _, position = uleb(data, position)
        _, position = uleb(data, position)
        _, position = uleb(data, position)
        fields, field_index = [], 0
        for _ in range(statics):
            difference, position = uleb(data, position)
            _, position = uleb(data, position)
            field_index += difference
            name = struct.unpack_from('<I', data, self.field_off + field_index * 8 + 4)[0]
            fields.append(self.string(name))
        count, position = uleb(data, static_values)
        values = {}
        for index in range(min(count, len(fields))):
            header = data[position]
            position += 1
            kind, argument = header & 0x1F, header >> 5
            if kind == 0x1E or kind == 0x1F:
                continue
            size = argument + 1
            if kind == 0x17:
                reference = int.from_bytes(data[position:position + size], 'little')
                values[fields[index]] = self.string(reference)
            elif kind in (0x1C, 0x1D):
                break  # Nested arrays and annotations never hold version constants.
            position += size
        return values


# IL2CPP metadata ------------------------------------------------------------

def read_il2cpp(path):
    """Returns (version, identifier strings, string literals) for an unprotected metadata file."""
    data = path.read_bytes()
    magic, version = struct.unpack_from('<II', data, 0)
    if magic != 0xFAB11BAF:
        raise ValueError(f'Metadata magic 0x{magic:08x} is not IL2CPP: protected or encrypted')
    if version >= 38:
        # Each section is an (offset, size, count) triple; literals store only their start.
        literal_off, _, literal_count = struct.unpack_from('<III', data, 8)
        data_off, data_size, _ = struct.unpack_from('<III', data, 20)
        name_off, name_size, _ = struct.unpack_from('<III', data, 32)
        starts = struct.unpack_from(f'<{literal_count}I', data, literal_off)
        ends = list(starts[1:]) + [data_size]
        literals = [data[data_off + start:data_off + end] for start, end in zip(starts, ends) if end > start]
    else:
        literal_off, literal_size, data_off, data_size, name_off, name_size = struct.unpack_from('<6I', data, 8)
        literals = []
        for index in range(literal_size // 8):
            length, start = struct.unpack_from('<II', data, literal_off + index * 8)
            if start + length <= data_size:
                literals.append(data[data_off + start:data_off + start + length])
    names = data[name_off:name_off + name_size].split(b'\0')
    decode = lambda raw: raw.decode('utf-8', 'replace')
    return version, sorted({decode(raw) for raw in names if raw}), [decode(raw) for raw in literals]


V31_SECTIONS = ('stringLiteral', 'stringLiteralData', 'string', 'events', 'properties', 'methods',
                'parameterDefaultValues', 'fieldDefaultValues', 'fieldAndParameterDefaultValueData',
                'fieldMarshaledSizes', 'parameters', 'fields', 'genericParameters',
                'genericParameterConstraints', 'genericContainers', 'nestedTypes', 'interfaces',
                'vtableMethods', 'interfaceOffsets', 'typeDefinitions', 'images', 'assemblies')


def read_il2cpp_types(path):
    """Assemblies, types, fields and methods of a v31 metadata file, without the native binary.

    Useful on ARM32 builds, where Cpp2IL is very slow and recovers no bodies. Names only.
    """
    data = path.read_bytes()
    magic, version = struct.unpack_from('<II', data, 0)
    if magic != 0xFAB11BAF or version != 31:
        raise ValueError(f'Type listing supports metadata v31, not {version}')
    sections = {name: struct.unpack_from('<II', data, 8 + index * 8) for index, name in enumerate(V31_SECTIONS)}
    type_size, field_size, method_size, image_size = 88, 12, 36, 40
    for name, size in (('typeDefinitions', type_size), ('fields', field_size), ('methods', method_size), ('images', image_size)):
        if sections[name][1] % size:
            raise ValueError(f'Unexpected {name} layout: not a v31 file after all')

    def text(index):
        start = sections['string'][0] + index
        return data[start:data.index(b'\0', start)].decode('utf-8', 'replace')

    def names(section, start, count, size):
        if start < 0:
            return []
        base = sections[section][0]
        return [text(struct.unpack_from('<I', data, base + (start + item) * size)[0]) for item in range(count)]

    for image in range(sections['images'][1] // image_size):
        name, _, first, count = struct.unpack_from('<IIII', data, sections['images'][0] + image * image_size)
        for index in range(first, first + count):
            base = sections['typeDefinitions'][0] + index * type_size
            type_name, namespace = struct.unpack_from('<II', data, base)
            field_start, method_start = struct.unpack_from('<ii', data, base + 32)
            methods, _, fields = struct.unpack_from('<HHH', data, base + 64)
            prefix = text(namespace)
            yield {'asm': text(name), 'type': (prefix + '.' if prefix else '') + text(type_name),
                   'fields': names('fields', field_start, fields, field_size),
                   'methods': names('methods', method_start, methods, method_size)}


# Scan -----------------------------------------------------------------------

def write_lines(path, lines):
    with path.open('w', errors='replace') as stream:
        for line in lines:
            stream.write(line.replace('\n', '\\n').replace('\r', '') + '\n')


def scan(unzipped, output):
    unzipped, output = Path(unzipped).resolve(strict=True), Path(output).resolve()
    try:
        output.relative_to(REPOSITORY)
    except ValueError:
        pass
    else:
        raise ValueError('The output folder must be outside this repository')
    output.mkdir(parents=True, exist_ok=True)
    report = {'manifest': None, 'versions': {}, 'sdks': {}, 'adapters': {}, 'buildconfig_versions': {},
              'top_packages': [], 'endpoints': [], 'il2cpp': None, 'config_files': [], 'warnings': []}

    manifest = unzipped / 'AndroidManifest.xml'
    if manifest.exists():
        try:
            report['manifest'] = read_manifest(manifest)
        except (ValueError, struct.error, IndexError) as exc:
            report['warnings'].append(f'Manifest parse failed: {exc}')

    for path in sorted(unzipped.glob('*.properties')):
        match = re.search(r'(?m)^version=(.+)$', path.read_text(errors='replace'))
        if match:
            report['versions'][path.stem] = match.group(1).strip()
    for path in sorted((unzipped / 'META-INF').glob('*.version')) if (unzipped / 'META-INF').exists() else []:
        report['versions'][path.stem] = path.read_text(errors='replace').strip()

    counts, packages, strings, domains = {}, {}, set(), set()
    known_prefixes = tuple(item for _, _, prefixes in SDKS for item in prefixes) + VENDOR_PREFIXES
    publisher_packages, publisher_dex = {}, {}
    for path in sorted(unzipped.glob('classes*.dex')):
        try:
            dex = Dex(path.read_bytes())
        except ValueError as exc:
            report['warnings'].append(f'{path.name}: {exc}')
            continue
        for row in dex.classes():
            name = dex.type_name(row[0])[1:-1]
            prefix = '/'.join(name.split('/')[:3])
            packages[prefix] = packages.get(prefix, 0) + 1
            publisher = name.startswith('saygames/') or not name.startswith(known_prefixes)
            if publisher:
                publisher_packages[prefix] = publisher_packages.get(prefix, 0) + 1
                publisher_dex[path.name] = publisher_dex.get(path.name, 0) + 1
            for category, label, prefixes in SDKS:
                if any(name.startswith(item) for item in prefixes):
                    entry = counts.setdefault(category, {}).setdefault(label, 0)
                    counts[category][label] = entry + 1
                    break
            for kind, pattern in ADAPTER_ROOTS.items():
                match = pattern.match(name)
                if match:
                    report['adapters'].setdefault(kind, set()).add(match.group(1))
            if name.endswith('/BuildConfig'):
                try:
                    values = dex.static_strings(row)
                except (struct.error, IndexError, ValueError):
                    values = {}
                version = values.get('VERSION_NAME') or values.get('SDK_VERSION') or values.get('VERSION')
                if version:
                    report['buildconfig_versions'][name[:-len('/BuildConfig')].replace('/', '.')] = version
        for text in dex.strings():
            if 3 <= len(text) <= 400:
                strings.add(text)
                domains.update(URL.findall(text))
    report['sdks'] = counts
    report['adapters'] = {kind: sorted(values) for kind, values in report['adapters'].items()}
    report['top_packages'] = sorted(packages.items(), key=lambda item: -item[1])[:120]
    report['publisher_packages'] = sorted(publisher_packages.items(), key=lambda item: -item[1])[:60]
    report['publisher_dex'] = publisher_dex
    report['endpoints'] = sorted(domains)
    write_lines(output / 'dex_strings.txt', sorted(strings))
    write_lines(output / 'dex_strings_money.txt', sorted(text for text in strings if MONEY_WORDS.search(text)))

    metadata = next(iter(sorted(unzipped.rglob('global-metadata.dat'))), None)
    if metadata:
        try:
            version, names, literals = read_il2cpp(metadata)
        except (ValueError, struct.error) as exc:
            report['warnings'].append(str(exc))
        else:
            unique = sorted(set(literals))
            report['il2cpp'] = {'metadata_version': version, 'identifiers': len(names), 'literals': len(unique)}
            write_lines(output / 'il2cpp_names.txt', names)
            write_lines(output / 'il2cpp_literals.txt', unique)
            write_lines(output / 'il2cpp_names_money.txt', [text for text in names if MONEY_WORDS.search(text) and len(text) <= MAX_NAME])
            write_lines(output / 'il2cpp_literals_money.txt', [text for text in unique if MONEY_WORDS.search(text)])
            if version == 31:
                try:
                    write_lines(output / 'il2cpp_types.jsonl', (json.dumps(row, ensure_ascii=False) for row in read_il2cpp_types(metadata)))
                except (ValueError, struct.error) as exc:
                    report['warnings'].append(f'Type listing skipped: {exc}')

    assets = unzipped / 'assets'
    if assets.exists():
        for path in sorted(assets.iterdir()):
            if path.is_file() and path.suffix.lower() in {'.json', '.csv', '.txt', '.xml', '.config', '.ini', '.yaml', '.yml', '.properties'}:
                report['config_files'].append({'path': str(path.relative_to(unzipped)), 'bytes': path.stat().st_size})
    (output / 'scan.json').write_text(json.dumps(report, indent=1, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('unzipped', type=Path, help='the unzipped/ folder from unpack_package.py')
    parser.add_argument('output', type=Path, help='evidence folder, outside this repository')
    args = parser.parse_args()
    try:
        report = scan(args.unzipped, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Scan failed: {exc}\n')
    manifest = report['manifest'] or {}
    print(json.dumps({'package': manifest.get('package'), 'version': manifest.get('versionName'),
                      'sdks': {key: sorted(value) for key, value in report['sdks'].items()},
                      'il2cpp': report['il2cpp'], 'warnings': report['warnings']}, indent=1))


if __name__ == '__main__':
    sys.exit(main())
