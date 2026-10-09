"""Literal evidence matching with offsets into the original source string."""
from array import array
from bisect import bisect_right
from dataclasses import asdict, dataclass
import hashlib
import re


@dataclass(frozen=True)
class Match:
    start: int
    end: int
    line_start: int
    line_end: int
    text: str


@dataclass(frozen=True)
class Result:
    status: str
    ok: bool
    source_sha256: str
    matches: tuple[Match, ...] = ()
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def fingerprint(source: str) -> str:
    """SHA-256 of the source string encoded as UTF-8, without newline normalization."""
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def _fold(text: str):
    # Each folded character maps to a half-open span of original characters.
    chars, starts, ends = [], array('I'), array('I')
    for match in re.finditer(r'\s+|\S', text):
        chars.append(' ' if match[0].isspace() else match[0])
        starts.append(match.start())
        ends.append(match.end())
    return ''.join(chars), starts, ends


def _find(source: str, quote: str, mode: str, offset: int):
    if mode == 'whitespace':
        haystack, starts, ends = _fold(source)
        needle = re.sub(r'\s+', ' ', quote).strip()
    else:
        haystack, needle = source, quote
    found = []
    position = 0
    while len(found) < 2:
        start = haystack.find(needle, position)
        if start < 0:
            break
        end = start + len(needle)
        span = (starts[start], ends[end - 1]) if mode == 'whitespace' else (start, end)
        found.append((span[0] + offset, span[1] + offset))
        position = start + 1  # Overlapping occurrences also count as ambiguous.
    return found


def verify(quote: str, source: str, *, mode: str = 'exact',
           lines: tuple[int, int] | list[int] | None = None,
           source_sha256: str | None = None) -> Result:
    """Check one quotation. Lines are inclusive, 1-based; offsets are 0-based.

    Exact mode preserves case, punctuation, and all whitespace. Whitespace mode
    folds Unicode whitespace and ignores quote-edge whitespace, but nothing else.
    At most two matches are returned: two means at least two occurrences.
    A supplied line range narrows the search and can disambiguate repetitions.
    """
    if not isinstance(quote, str) or not isinstance(source, str):
        raise ValueError('quote and source must be strings')
    if mode not in ('exact', 'whitespace'):
        raise ValueError('mode must be exact or whitespace')
    digest = fingerprint(source)
    if source_sha256 is not None:
        if not isinstance(source_sha256, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', source_sha256):
            raise ValueError('source_sha256 must be a 64-character SHA-256 hex digest')
        if digest != source_sha256.lower():
            return Result('SOURCE_CHANGED', False, digest, detail='Source text differs from the supplied fingerprint.')
    if not quote.strip():
        return Result('EMPTY_QUOTE', False, digest, detail='A quotation must contain non-whitespace text.')
    line_starts = [0] + [m.end() for m in re.finditer(r'\r\n|\r|\n', source)]
    # A terminal newline is not an additional physical line.
    if len(line_starts) > 1 and line_starts[-1] == len(source):
        line_starts.pop()
    start, end = 0, len(source)
    if lines is not None:
        if not isinstance(lines, (tuple, list)) or len(lines) != 2 or any(type(n) is not int for n in lines):
            raise ValueError('lines must be two integer line numbers')
        first, last = lines
        if first < 1 or last < first or last > len(line_starts):
            return Result('INVALID_LINES', False, digest, detail='Line range is outside the source or is reversed.')
        start = line_starts[first - 1]
        end = line_starts[last] if last < len(line_starts) else len(source)
    spans = _find(source[start:end], quote, mode, start)
    if not spans:
        if lines is not None and _find(source, quote, mode, 0):
            return Result('WRONG_LOCATION', False, digest, detail='Quote exists, but not within the supplied lines.')
        return Result('NOT_FOUND', False, digest, detail='Quote is absent under the selected matching mode.')
    matches = tuple(Match(a, b, bisect_right(line_starts, a),
                          bisect_right(line_starts, b - 1), source[a:b]) for a, b in spans)
    if len(matches) > 1:
        return Result('AMBIGUOUS', False, digest, matches, 'At least two occurrences; provide a narrower line range.')
    status = 'EXACT' if matches[0].text == quote else 'WHITESPACE'
    return Result(status, True, digest, matches)
