"""Synthetic sample data only: no game names, no real numbers."""
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from toolkit.build_monetization_page import REPOSITORY, TEMPLATE, build, check_page

SAMPLE = REPOSITORY / 'templates' / 'MONETIZATION_PAGE_DATA.json'


def sample():
    return json.loads(SAMPLE.read_text(encoding='utf-8'))


class CheckTests(unittest.TestCase):
    def problems(self, change):
        page = sample()
        change(page)
        return check_page(page, TEMPLATE.read_text(encoding='utf-8'))

    def test_sample_is_clean(self):
        self.assertEqual(self.problems(lambda page: None), [])

    def test_unknown_rival(self):
        problems = self.problems(lambda page: page['cards'][0]['who'].append('nobody'))
        self.assertIn('nobody is not a rival', problems[0])

    def test_unknown_state(self):
        problems = self.problems(lambda page: page['cards'][0]['ours'].update(ours1=['maybe', 'text']))
        self.assertIn('unknown state maybe', problems[0])

    def test_card_must_cover_all_our_games(self):
        problems = self.problems(lambda page: page['cards'][0]['ours'].pop('ours1'))
        self.assertIn('ours must cover', problems[0])

    def test_missing_template_string(self):
        problems = self.problems(lambda page: page['ui'].pop('tryIt'))
        self.assertEqual(problems, ['missing ui string: tryIt'])

    def test_unknown_game_in_chart(self):
        problems = self.problems(lambda page: page['charts'][0]['rows'].append({'game': 'nobody', 'value': 1, 'label': '1'}))
        self.assertEqual(problems, ['unknown game id: nobody'])

    def test_keys_stop_the_build_and_stay_masked(self):
        secret = 'ca-app-pub-1234567890123456'
        problems = self.problems(lambda page: page['cards'][0].update(them=f'unit {secret}'))
        self.assertEqual(len(problems), 1)
        self.assertNotIn(secret, problems[0])


class BuildTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def bundle(self, *pages):
        files = []
        for index, page in enumerate(pages):
            path = self.folder / f'data{index}.json'
            path.write_text(json.dumps(page), encoding='utf-8')
            files.append(path)
        written = build(files, self.folder / 'page.html').read_text(encoding='utf-8')
        block = re.search(r'<script id="page-data" type="application/json">(.*?)</script>', written, re.S).group(1)
        return json.loads(block)

    def test_two_languages_share_one_icon_map(self):
        (self.folder / 'a.png').write_bytes(b'\x89PNG')
        first = sample()
        first['games'][0]['icon'] = 'a.png'
        second = copy.deepcopy(first)
        second['lang'] = 'ru'
        bundle = self.bundle(first, second)
        self.assertEqual(sorted(bundle['pages']), ['en', 'ru'])
        self.assertTrue(bundle['icons'][first['games'][0]['id']].startswith('data:image/png;base64,'))
        self.assertNotIn('icon', bundle['pages']['ru']['games'][0])

    def test_remote_icon_is_refused(self):
        page = sample()
        page['games'][0]['icon'] = 'https://example.com/a.png'
        with self.assertRaises(ValueError):
            self.bundle(page)

    def test_string_cannot_close_the_script_block(self):
        page = sample()
        page['answer'] = 'a </script><script>alert(1)</script>'
        self.assertEqual(self.bundle(page)['pages']['en']['answer'], page['answer'])

    def test_refuses_output_inside_repository(self):
        with self.assertRaises(ValueError):
            build([SAMPLE], REPOSITORY / 'page.html')


class TemplateTests(unittest.TestCase):
    def test_only_fonts_load_from_outside(self):
        links = re.findall(r'(?:src|href)="(https?://[^"]+)"', TEMPLATE.read_text(encoding='utf-8'))
        self.assertTrue(links)
        self.assertTrue(all('fonts.g' in link for link in links), links)

    @unittest.skipUnless(shutil.which('node'), 'node is not installed')
    def test_script_parses(self):
        html = TEMPLATE.read_text(encoding='utf-8')
        script = html[html.rindex('<script>') + 8:html.rindex('</script>')]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'page.js'
            path.write_text(script, encoding='utf-8')
            self.assertEqual(subprocess.run(['node', '--check', str(path)], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
