import re
import unittest

import lexer


class CreateLexerTest(unittest.TestCase):

    def test_create_lexer_happy_flow(self) -> None:
        rules = r'''
            # Example comment
            Whitespace[emit=false]  r'\s+'
            
            Float                      r'[0-9]*\.[0-9]*'
            Integer                    '[0-9]+'  # Only matches if Float did not match
            String                     '"[^"]*"'
            Keyword[ignore_case=true]  'goto|if'
            Identifier[to_upper=true]  '[a-zA-Z][a-zA-Z0-9_]*'
        '''
        l = lexer.Lexer(rules)
        expected_ids = ['Whitespace', 'Float', 'Integer', 'String', 'Keyword', 'Identifier']
        self.assertEqual(expected_ids, [token.id for token in l._token_matchers])
        expected_emit = [False, True, True, True, True, True]
        expected_to_upper = [False, False, False, False, False, True]
        expected_ignore_case = [False, False, False, False, True, False]
        self.assertEqual(expected_emit, [token.emit for token in l._token_matchers])
        self.assertEqual(expected_to_upper, [token.to_upper for token in l._token_matchers])
        self.assertEqual(
            expected_ignore_case,
            [(token.regexp.flags & re.RegexFlag.IGNORECASE) != 0 for token in l._token_matchers]
        )

    def test_create_lexer_invalid_regex(self) -> None:
        rules = r'''
            Whitespace  r'\s+'
            Float       '[0-'
        '''
        with self.assertRaisesRegex(lexer.LexerError, 'Invalid matching rule'):
            lexer.Lexer(rules)

    def test_create_lexer_invalid_expression(self) -> None:
        rules = r'''
            Whitespace  r'\s+'
            Float       0-9
        '''
        with self.assertRaisesRegex(lexer.LexerError, 'Invalid matching rule'):
            lexer.Lexer(rules)


class LexerTokenizerTest(unittest.TestCase):

    def test_parse_arithmetic(self) -> None:
        l = lexer.Lexer(r'''
            WS         r"\s+"
            Number     r'[0-9]+(\.[0-9]*)?'
            Operator   r'\+|\-|\*|\/'
        ''')
        tokens = list(l.tokenize('5   + 7.5'))
        self.assertEqual([token.value for token in tokens], ['5', '   ', '+', ' ', '7.5'])
        self.assertEqual([token.token_id for token in tokens], ['Number', 'WS', 'Operator', 'WS', 'Number'])

    def test_parse_with_emit_false_and_to_upper(self) -> None:
        l = lexer.Lexer(r'''
            WS[emit=false]              r'\s+'
            Identifier[to_upper=true]   r'[a-zA-Z][a-zA-Z0-9_]*'
            Arrow                        '->'
        ''')
        tokens = list(l.tokenize('Root   ->   Foo Bar Baz'))
        # Whitespace is not emitted.
        self.assertEqual([token.value for token in tokens], ['ROOT', '->', 'FOO', 'BAR', 'BAZ'])

    def test_parse_with_ignore_case(self) -> None:
        l = lexer.Lexer(r'''
            WS[emit=false]              r'\s+'
            Keyword[ignore_case=true]   r'[a-z][a-z0-9_]*'
            Arrow                        '->'
        ''')
        tokens = list(l.tokenize('Root   ->   Foo Bar Baz'))
        # Whitespace is not emitted.
        self.assertEqual([token.value for token in tokens], ['Root', '->', 'Foo', 'Bar', 'Baz'])

    def test_parse_with_ignore_case_and_to_upper(self) -> None:
        l = lexer.Lexer(r'''
            WS[emit=false]              r'\s+'
            Keyword[ignore_case=true,to_upper=true]   r'[a-z][a-z0-9_]*'
            Arrow                        '->'
        ''')
        tokens = list(l.tokenize('Root   ->   Foo Bar Baz'))
        # Whitespace is not emitted.
        self.assertEqual([token.value for token in tokens], ['ROOT', '->', 'FOO', 'BAR', 'BAZ'])

    def test_fail_to_parse(self) -> None:
        l = lexer.Lexer(r'''
            WS[emit=false]   r'\s+'
            Identifier   r'[a-zA-Z][a-zA-Z0-9_]*'
            Arrow        '->'
        ''')
        with self.assertRaisesRegex(lexer.LexerError, 'Failed to match any token at position 4'):
            list(l.tokenize('Foo !'))


if __name__ == '__main__':
    unittest.main()
