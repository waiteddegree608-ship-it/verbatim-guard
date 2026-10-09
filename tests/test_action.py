"""Exercise the real action entrypoint in isolated child processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'action' / 'run.py'


class ActionTests(unittest.TestCase):
    def run_action(self, bundle, mode='exact', raw=None, shadow=False):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path = root / 'evidence file.json'
            path.write_text(raw if raw is not None else json.dumps(bundle), encoding='utf-8')
            if shadow:
                (root / 'json.py').write_text('raise RuntimeError("checkout executed")', encoding='utf-8')
            output, summary = root / 'output', root / 'summary'
            env = dict(os.environ, VG_BUNDLE=str(path), VG_MODE=mode,
                       GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary), PYTHONPATH=str(root))
            result = subprocess.run([sys.executable, '-I', str(RUNNER)], cwd=root,
                                    env=env, capture_output=True, text=True, encoding='utf-8')
            return result, output.read_text(encoding='utf-8'), summary.read_text(encoding='utf-8')

    def bundle(self, quote='48 participants', identifier='sample'):
        return {'sources': {'paper': '48 participants'},
                'claims': [{'id': identifier, 'source': 'paper', 'quote': quote}]}

    def test_pass_outputs_summary_and_isolated_checkout(self):
        result, outputs, summary = self.run_action(self.bundle(), shadow=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('input-valid=true\nok=true\npassed=1\nfailed=0\ntotal=1\n', outputs)
        self.assertIn('| EXACT | 1 |', summary)
        self.assertNotIn('::error', result.stdout)

    def test_failed_evidence_is_a_failed_step(self):
        result, outputs, summary = self.run_action(self.bundle('480 participants'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('::error title=Verbatim Guard::NOT_FOUND:', result.stdout)
        self.assertIn('failed=1', outputs)
        self.assertIn('| NOT_FOUND | 1 |', summary)
        self.assertNotIn('480 participants', result.stdout + summary)

    def test_opt_in_whitespace(self):
        result, _, summary = self.run_action(self.bundle('48\nparticipants'), mode='whitespace')
        self.assertEqual(result.returncode, 0)
        self.assertIn('| WHITESPACE | 1 |', summary)

    def test_duplicate_keys_are_invalid(self):
        result, outputs, summary = self.run_action(None, raw='{"sources":{},"sources":{},"claims":[]}')
        self.assertEqual(result.returncode, 2)
        self.assertIn('input-valid=false', outputs)
        self.assertIn('Invalid input', summary)

    def test_invalid_mode(self):
        result, outputs, _ = self.run_action(self.bundle(), mode='fuzzy')
        self.assertEqual(result.returncode, 2)
        self.assertIn('total=0', outputs)

    def test_ids_cannot_inject_commands_or_summary(self):
        malicious = 'bad%\n::notice::injected\r<img src=x>'
        result, _, summary = self.run_action(self.bundle('invented', malicious))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('\n::notice::', result.stdout)
        self.assertNotIn('<img', summary)
        self.assertIn('%25', result.stdout)

    def test_duplicate_key_error_cannot_inject_commands(self):
        key = 'bad\n::notice::injected'
        raw = '{' + json.dumps(key) + ':1,' + json.dumps(key) + ':2}'
        result, _, _ = self.run_action(None, raw=raw)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('\n::notice::', result.stdout)
        self.assertIn('%0A::notice::', result.stdout)

    def test_annotation_count_is_bounded(self):
        bundle = self.bundle('invented')
        bundle['claims'] = [dict(bundle['claims'][0], id=str(i)) for i in range(60)]
        result, outputs, summary = self.run_action(bundle)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count('::error title='), 50)
        self.assertIn('failed=60', outputs)
        self.assertIn('| NOT_FOUND | 60 |', summary)

    def test_oversize_bundle_is_invalid(self):
        result, _, _ = self.run_action(None, raw=' ' * (8 * 1024 * 1024 + 1))
        self.assertEqual(result.returncode, 2)
        self.assertIn('8 MiB', result.stdout)

    def test_deeply_nested_json_is_invalid(self):
        result, outputs, _ = self.run_action(None, raw='[' * 2000 + '0' + ']' * 2000)
        self.assertEqual(result.returncode, 2)
        self.assertIn('input-valid=false', outputs)


if __name__ == '__main__':
    unittest.main()
