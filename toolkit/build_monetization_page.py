"""Build the competitor comparison page: data files in, one self-contained HTML file out.

Copy templates/MONETIZATION_PAGE_DATA.json to your reports folder and fill it. Give one
data file per language and the page shows a language switch. Everything is checked first:
game ids must match, every template string must exist, and anything shaped like a key or
ad unit id stops the build. The output must be outside this repository. Standard library only.
"""
import argparse
import base64
import json
import mimetypes
from pathlib import Path
import re

REPOSITORY = Path(__file__).resolve().parent.parent
TEMPLATE = REPOSITORY / 'templates' / 'MONETIZATION_PAGE.html'
SLOT = '"__PAGE_DATA__"'
REQUIRED = ('lang', 'languageName', 'answer', 'hero', 'focus', 'goals', 'games', 'topics', 'cards', 'timeline', 'ladders',
            'charts', 'publishers', 'notBehind', 'sayIt', 'questions', 'limits', 'words', 'ui')
CARD_KEYS = ('topic', 'title', 'who', 'vs', 'them', 'ours', 'tryIt', 'effort', 'status')
STATES = {'gap', 'part', 'ok'}
SECRET = re.compile(r'ca-app-pub-\d+|\b[0-9a-fA-F]{32,}\b|\b[A-Za-z0-9_-]{64,}\b')


def template_strings(template):
    return set(re.findall(r'data-text="(\w+)"', template)) | set(re.findall(r'\bui\.(\w+)', template))


def strings_in(value, path=''):
    if isinstance(value, dict):
        for key, item in value.items():
            if key != 'icon':
                yield from strings_in(item, f'{path}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings_in(item, f'{path}[{index}]')
    elif isinstance(value, str):
        yield path, value


def check_card(number, card, topics, rivals, ours):
    problems = [f'card {number}: missing {key}' for key in CARD_KEYS if key not in card]
    if problems:
        return problems
    if card['topic'] not in topics:
        problems.append(f'card {number}: unknown topic {card["topic"]}')
    problems += [f'card {number}: {game} is not a rival' for game in set(card['who']) - rivals]
    if set(card['ours']) != ours:
        problems.append(f'card {number}: ours must cover exactly {sorted(ours)}')
    problems += [f'card {number}: {game} has unknown state {value[0]}' for game, value in card['ours'].items() if value[0] not in STATES]
    if len(card['vs']) != 2:
        problems.append(f'card {number}: vs needs two short texts')
    return problems


def check_page(page, template):
    """Every problem in one language's data, so one run shows them all."""
    problems = [f'missing key: {key}' for key in REQUIRED if key not in page]
    if problems:
        return problems
    problems += [f'missing ui string: {name}' for name in sorted(template_strings(template) - set(page['ui']))]
    ours = {game['id'] for game in page['games'] if game['side'] == 'us'}
    rivals = {game['id'] for game in page['games']} - ours
    if not ours or not rivals:
        problems.append('need at least one game on each side')
    topics = {topic[0] for topic in page['topics']}
    if 'all' not in topics:
        problems.append('topics need an "all" entry')
    for number, card in enumerate(page['cards'], 1):
        problems += check_card(number, card, topics, rivals, ours)
    used = [row['game'] for row in page['timeline']['rows']] + [row['game'] for row in page['ladders']['rows']]
    used += [row['game'] for chart in page['charts'] for row in chart['rows']]
    used += [game for publisher in page['publishers'] for game in publisher['games']]
    used += [row['game'] for row in page.get('stack', {}).get('rows', [])]
    problems += [f'unknown game id: {game}' for game in sorted(set(used) - ours - rivals)]
    for path, text in strings_in(page):
        for hit in SECRET.findall(text):
            problems.append(f'{path} looks like a key or ad unit id ({hit[:3]}...): mask it')
    return problems


def inline_icons(page, folder, icons):
    """Move each game's icon into one shared map, so languages do not repeat the bytes."""
    problems = []
    for game in page.get('games', []):
        icon = game.pop('icon', '')
        if not icon or game['id'] in icons:
            continue
        if icon.startswith('data:image/'):
            icons[game['id']] = icon
            continue
        path = folder / icon
        mime = mimetypes.guess_type(path.name)[0] or ''
        if '://' in icon or not path.is_file() or not mime.startswith('image/'):
            problems.append(f'{game["id"]}: icon must be a local image or a data URI, got {icon[:60]}')
            continue
        icons[game['id']] = f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()
    return problems


def build(data_files, output):
    output = Path(output).resolve()
    if output.is_relative_to(REPOSITORY):
        raise ValueError('The output must be outside this repository')
    template = TEMPLATE.read_text(encoding='utf-8')
    pages, icons, problems = {}, {}, []
    for data_file in map(Path, data_files):
        page = json.loads(data_file.read_text(encoding='utf-8'))
        found = check_page(page, template) + inline_icons(page, data_file.parent, icons)
        problems += [f'{data_file.name}: {problem}' for problem in found]
        pages[page.get('lang', data_file.stem)] = page
    if problems:
        raise ValueError('\n'.join(problems))
    # Escaping < keeps any string from closing the script block early.
    payload = json.dumps({'icons': icons, 'pages': pages}, ensure_ascii=False).replace('<', '\\u003c')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace(SLOT, payload), encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path, help='the HTML file to write')
    parser.add_argument('data', type=Path, nargs='+', help='one filled data file per language; the first is the default')
    args = parser.parse_args()
    try:
        written = build(args.data, args.output)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'Page not built:\n{exc}\n')
    print(f'{written} ({written.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()
