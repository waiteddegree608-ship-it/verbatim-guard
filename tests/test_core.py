import unittest
from verbatim_guard import fingerprint, verify


class EvidenceTests(unittest.TestCase):
    def test_exact_offsets_and_lines(self):
        text = 'Title\nThe trial included 48 participants.\nEnd.'
        result = verify('48 participants', text)
        self.assertEqual(result.status, 'EXACT')
        match = result.matches[0]
        self.assertEqual((match.line_start, match.line_end), (2, 2))
        self.assertEqual(text[match.start:match.end], '48 participants')

    def test_changed_number_fails(self):
        self.assertEqual(verify('480 participants', '48 participants').status, 'NOT_FOUND')

    def test_case_and_punctuation_are_not_folded(self):
        for quote in ['HELLO', 'hello!', '“hello”']:
            with self.subTest(quote=quote):
                self.assertFalse(verify(quote, 'hello', mode='whitespace').ok)

    def test_exact_mode_does_not_fold_whitespace(self):
        self.assertFalse(verify('one two', 'one\ntwo').ok)

    def test_folded_offsets_preserve_original(self):
        result = verify('one two three', 'X\none\r\n\t two\u00a0three\nY', mode='whitespace')
        self.assertEqual(result.status, 'WHITESPACE')
        self.assertEqual(result.matches[0].text, 'one\r\n\t two\u00a0three')
        self.assertEqual((result.matches[0].line_start, result.matches[0].line_end), (2, 3))

    def test_leading_and_trailing_whitespace_policy(self):
        self.assertFalse(verify(' word ', 'word').ok)
        self.assertTrue(verify(' word ', 'word', mode='whitespace').ok)

    def test_empty_quotes_rejected(self):
        for quote in ['', ' ', '\n\t', '\u00a0']:
            self.assertEqual(verify(quote, 'abc', mode='whitespace').status, 'EMPTY_QUOTE')

    def test_empty_source_does_not_pass(self):
        self.assertEqual(verify('abc', '').status, 'NOT_FOUND')

    def test_repeated_quote_is_ambiguous(self):
        result = verify('same', 'same\nsame\nsame')
        self.assertEqual(result.status, 'AMBIGUOUS')
        self.assertFalse(result.ok)
        self.assertEqual(len(result.matches), 2)

    def test_overlapping_quote_is_ambiguous(self):
        self.assertEqual(verify('aa', 'aaa').status, 'AMBIGUOUS')

    def test_lines_disambiguate_third_occurrence(self):
        result = verify('same', 'same\nsame\nsame', lines=(3, 3))
        self.assertTrue(result.ok)
        self.assertEqual(result.matches[0].start, 10)

    def test_correct_quote_wrong_line_fails(self):
        self.assertEqual(verify('answer', 'title\nanswer', lines=[1, 1]).status, 'WRONG_LOCATION')

    def test_cross_line_quote_cannot_escape_scope(self):
        result = verify('one two', 'one\ntwo', mode='whitespace', lines=[1, 1])
        self.assertEqual(result.status, 'WRONG_LOCATION')

    def test_line_break_formats(self):
        for newline in ['\n', '\r', '\r\n']:
            with self.subTest(newline=newline):
                result = verify('last', f'first{newline}last{newline}', lines=(2, 2))
                self.assertTrue(result.ok)
                self.assertEqual(result.matches[0].line_start, 2)
                self.assertEqual(verify('last', f'first{newline}last{newline}', lines=(3, 3)).status, 'INVALID_LINES')

    def test_invalid_line_ranges(self):
        for lines in [(0, 1), (2, 1), (1, 9), (-1, 1)]:
            self.assertEqual(verify('x', 'x', lines=lines).status, 'INVALID_LINES')

    def test_invalid_line_types(self):
        for lines in [[True, 1], [1.0, 1], [1], '1:2']:
            with self.assertRaises(ValueError):
                verify('x', 'x', lines=lines)

    def test_source_changed_even_if_quote_still_exists(self):
        old = 'a claim\nversion 1'
        result = verify('a claim', 'a claim\nversion 2', source_sha256=fingerprint(old))
        self.assertEqual(result.status, 'SOURCE_CHANGED')

    def test_correct_hash_passes(self):
        self.assertTrue(verify('x', 'x', source_sha256=fingerprint('x').upper()).ok)

    def test_malformed_hash_rejected(self):
        for digest in ['x', 1, 'z' * 64]:
            with self.assertRaises(ValueError):
                verify('x', 'x', source_sha256=digest)

    def test_cjk_and_emoji_offsets(self):
        text = '标题\n🧪 实验包含48名参与者。'
        result = verify('实验包含48名参与者。', text)
        match = result.matches[0]
        self.assertEqual(text[match.start:match.end], '实验包含48名参与者。')
        self.assertEqual(match.line_start, 2)

    def test_unicode_normalization_is_not_implicit(self):
        self.assertFalse(verify('café', 'cafe\u0301', mode='whitespace').ok)

    def test_mode_and_input_type_validation(self):
        with self.assertRaises(ValueError):
            verify('a', 'a', mode='fuzzy')
        with self.assertRaises(ValueError):
            verify(None, 'a')

    def test_normalized_span_mapping_exhaustive_whitespace(self):
        for gap in [' ', '\n', '\r\n', '\t', '\u00a0', '  \n\t']:
            source = 'prefix ' + 'alpha' + gap + 'beta' + ' suffix'
            result = verify('alpha beta', source, mode='whitespace')
            self.assertTrue(result.ok)
            match = result.matches[0]
            self.assertEqual(source[match.start:match.end], 'alpha' + gap + 'beta')
