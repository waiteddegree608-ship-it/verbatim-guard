"""Run the bundled validator without installing dependencies or reading checkout code."""
from collections import Counter
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from verbatim_guard import check_bundle
from verbatim_guard.cli import load_bundle


def escape_command(text):
    # Workflow commands must not be injectable through untrusted bundle strings.
    return str(text).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def annotation(message):
    print('::error title=Verbatim Guard::' + escape_command(message))


def write_outputs(valid, ok=False, passed=0, failed=0, total=0):
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as stream:
            stream.write(f'input-valid={str(valid).lower()}\nok={str(ok).lower()}\n'
                         f'passed={passed}\nfailed={failed}\ntotal={total}\n')


def write_summary(report):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:
        return
    # Only fixed status names and numeric counts, never source excerpts or IDs.
    if report is None:
        text = '### Verbatim Guard\n\nInvalid input. No quotations were checked. See the error annotation.\n'
    else:
        summary = report['summary']
        text = (f"### Verbatim Guard\n\n{summary['passed']} / {summary['total']} quotations passed "
                f"({report['mode']} mode).\n\n| Status | Count |\n| --- | ---: |\n")
        text += ''.join(f'| {status} | {count} |\n' for status, count in sorted(Counter(
            row['status'] for row in report['results']).items()))
        text += '\nMatching text does not establish factual truth or semantic support.\n'
    with open(path, 'a', encoding='utf-8') as stream:
        stream.write(text)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        path = os.environ.get('VG_BUNDLE', '')
        if not path or path == '-':
            raise ValueError('bundle must name a JSON file; stdin is not supported by the action')
        report = check_bundle(load_bundle(path), mode=os.environ.get('VG_MODE', 'exact'))
    except (ValueError, OSError, UnicodeError, RecursionError) as error:
        annotation('Invalid input: ' + str(error)[:1500])
        write_outputs(False)
        write_summary(None)
        return 2
    write_outputs(True, report['ok'], **report['summary'])
    write_summary(report)
    failures = [row for row in report['results'] if not row['ok']]
    for row in failures[:50]:
        annotation(f"{row['status']}: claim {row['id'][:200]!r}, source {row['source'][:200]!r}. {row['detail']}")
    if len(failures) > 50:
        print(f'{len(failures) - 50} additional failures omitted from annotations; see summary counts.')
    summary = report['summary']
    print(f"Verbatim Guard: {summary['passed']}/{summary['total']} passed; {summary['failed']} failed.")
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
