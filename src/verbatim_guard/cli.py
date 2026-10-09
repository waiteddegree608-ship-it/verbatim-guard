"""CLI: 0 = all checks pass, 1 = failed evidence checks, 2 = invalid input."""
import argparse
import html
from importlib.resources import files
import json
from pathlib import Path
import sys

from . import __version__
from .bundle import check_bundle

MAX_BYTES = 8 * 1024 * 1024


def render_text(report):
    lines = [f'Verbatim Guard | {report["mode"]} mode', '']
    for row in report['results']:
        where = ', '.join(f'L{m["line_start"]}-{m["line_end"]}' for m in row['matches'])
        lines.append(f'{row["status"]:<16} {row["id"]} ({row["source"]})' + (f'  {where}' if where else ''))
    s = report['summary']
    lines += ['', f'{s["passed"]}/{s["total"]} passed; {s["failed"]} need attention.',
              'Text matching does not establish factual truth or semantic support.']
    return '\n'.join(lines) + '\n'


def render_html(report):
    rows = []
    for row in report['results']:
        matches = ''.join(f'<pre>L{m["line_start"]}–{m["line_end"]}: {html.escape(m["text"])}</pre>' for m in row['matches'])
        cells = ''.join(f'<td>{html.escape(str(row[k]))}</td>' for k in ('status', 'id', 'source'))
        rows.append(f'<tr class="{"pass" if row["ok"] else "fail"}">{cells}<td>{matches}{html.escape(row["detail"])}</td></tr>')
    s = report['summary']
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Verbatim Guard — evidence report</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;margin:40px auto;padding:0 20px;max-width:1100px;background:#101820;color:#e5edf3}}h1{{font-size:40px}}.tag{{color:#75d5c0}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%}}th,td{{padding:14px;text-align:left;border-bottom:1px solid #32434f;vertical-align:top}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;margin:0}}td{{overflow-wrap:anywhere}}.pass td:first-child{{color:#75d5c0}}.fail td:first-child{{color:#ffbe82}}footer{{color:#a5b9c8;margin-top:28px}}</style>
<header><p class="tag">LOCAL · DETERMINISTIC · NO MODEL CALLS</p><h1>Verbatim Guard</h1>
<p>{s['passed']} / {s['total']} quotations passed · {html.escape(report['mode'])} mode</p></header>
<main class="scroll"><table><thead><tr><th>Status</th><th>Claim</th><th>Source</th><th>Evidence</th></tr></thead><tbody>{''.join(rows)}</tbody></table></main>
<footer>Matching text is not proof that a claim is true. This report checks only supplied text, locations, and optional fingerprints. Source excerpts may be sensitive; review before sharing.</footer></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description='Check quotations against supplied source text. No API key or network calls.')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'demo'):
        command = sub.add_parser(name)
        if name == 'check':
            command.add_argument('bundle', help='UTF-8 JSON bundle, or - for stdin')
        command.add_argument('--mode', choices=('exact', 'whitespace'), default='exact')
        command.add_argument('--format', choices=('text', 'json', 'html'), default='text')
        command.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            raw = files('verbatim_guard').joinpath('demo.json').read_bytes()
        elif args.bundle == '-':
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with open(args.bundle, 'rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Input exceeds the 8 MiB limit')
        def unique_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate JSON key: ' + key)
                result[key] = value
            return result
        bundle = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_keys)
        report = check_bundle(bundle, mode=args.mode)
        rendered = (json.dumps(report, ensure_ascii=False, indent=2) + '\n' if args.format == 'json'
                    else render_html(report) if args.format == 'html' else render_text(report))
        if args.output:
            args.output.write_text(rendered, encoding='utf-8')
        else:
            sys.stdout.write(rendered)
        # Demo deliberately includes bad quotations; its exit code remains 1.
        return 0 if report['ok'] else 1
    except (ValueError, OSError, UnicodeError) as error:
        print(f'verbatim-guard: {error}', file=sys.stderr)
        return 2
