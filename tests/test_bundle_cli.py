import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from verbatim_guard import check_bundle
from verbatim_guard.cli import render_html


def example(quote='A real sentence.'):
    return {'sources': {'doc': 'A real sentence.'},
            'claims': [{'id': 'c1', 'source': 'doc', 'quote': quote}]}


class BundleTests(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(check_bundle(example())['summary'], {'total': 1, 'passed': 1, 'failed': 0})

    def test_unknown_source_is_not_opened(self):
        bundle = example()
        bundle['claims'][0]['source'] = '../../secret.txt'
        self.assertEqual(check_bundle(bundle)['results'][0]['status'], 'MISSING_SOURCE')

    def test_reject_unknown_fields(self):
        bundle = example()
        bundle['claims'][0]['linez'] = [1, 1]
        with self.assertRaises(ValueError):
            check_bundle(bundle)

    def test_duplicate_claim_id(self):
        bundle = example()
        bundle['claims'] *= 2
        with self.assertRaises(ValueError):
            check_bundle(bundle)

    def test_empty_batch_not_a_vacuous_pass(self):
        bundle = example()
        bundle['claims'] = []
        with self.assertRaises(ValueError):
            check_bundle(bundle)

    def test_invalid_source_text(self):
        bundle = example()
        bundle['sources']['doc'] = {'path': 'source.txt'}
        with self.assertRaises(ValueError):
            check_bundle(bundle)

    def test_html_escapes_untrusted_text(self):
        payload = '<script>alert(1)</script>'
        bundle = {'sources': {payload: payload}, 'claims': [{'id': payload, 'source': payload, 'quote': payload}]}
        page = render_html(check_bundle(bundle))
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn("default-src 'none'", page)


class CLITests(unittest.TestCase):
    def call(self, *args, data=None):
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        return subprocess.run([sys.executable, '-m', 'verbatim_guard', *args],
                              input=data, capture_output=True, encoding='utf-8', env=env)

    def test_pass_exit_code_and_json(self):
        run = self.call('check', '-', '--format', 'json', data=json.dumps(example()))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)['ok'])

    def test_fail_exit_code(self):
        run = self.call('check', '-', data=json.dumps(example('Made up sentence.')))
        self.assertEqual(run.returncode, 1)
        self.assertIn('NOT_FOUND', run.stdout)

    def test_bad_json_exit_code(self):
        run = self.call('check', '-', data='{')
        self.assertEqual(run.returncode, 2)
        self.assertNotIn('Traceback', run.stderr)

    def test_duplicate_json_keys_rejected(self):
        run = self.call('check', '-', data='{"sources":{},"sources":{},"claims":[]}')
        self.assertEqual(run.returncode, 2)
        self.assertIn('Duplicate JSON key', run.stderr)

    def test_missing_file(self):
        run = self.call('check', 'there-is-no-such-file.json')
        self.assertEqual(run.returncode, 2)

    def test_demo_is_self_contained(self):
        run = self.call('demo', '--mode', 'whitespace', '--format', 'json')
        self.assertEqual(run.returncode, 1)
        report = json.loads(run.stdout)
        self.assertEqual(report['summary'], {'total': 6, 'passed': 2, 'failed': 4})

    def test_output_and_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = str(Path(directory) / '报告.html')
            run = self.call('demo', '--format', 'html', '--output', target)
            self.assertEqual(run.returncode, 1)
            self.assertIn('Verbatim Guard', Path(target).read_text(encoding='utf-8'))
            self.assertEqual(run.stdout, '')

    def test_cli_input_limit(self):
        run = self.call('check', '-', data=' ' * (8 * 1024 * 1024 + 1))
        self.assertEqual(run.returncode, 2)
        self.assertIn('8 MiB', run.stderr)
