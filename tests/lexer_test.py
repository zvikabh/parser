import unittest

import lexer


class CreateLexerTest(unittest.TestCase):

    def test_create_lexer_happy_flow(self):
        rules = r'''
            # Example comment
            Whitespace[emit=false]  r'\s+'
            
            Float       r'[0-9]*\.[0-9]*'
            Integer     '[0-9]+'  # Only matches if Float did not match
            String      '"[^"]*"'
            Identifier  '[a-zA-Z][a-zA-Z0-9_]*'
        '''
        l = lexer.Lexer(rules)
        expected_ids = ['Whitespace', 'Float', 'Integer', 'String', 'Identifier']
        self.assertEqual(expected_ids, [token.id for token in l._token_matchers])
        expected_emit = [False, True, True, True, True]
        self.assertEqual(expected_emit, [token.emit for token in l._token_matchers])

    def test_create_lexer_invalid_regex(self):
        rules = r'''
            Whitespace  r'\s+'
            Float       '[0-'
        '''
        with self.assertRaisesRegex(lexer.LexerError, 'Invalid matching rule'):
            lexer.Lexer(rules)

    def test_create_lexer_invalid_expression(self):
        rules = r'''
            Whitespace  r'\s+'
            Float       0-9
        '''
        with self.assertRaisesRegex(lexer.LexerError, 'Invalid matching rule'):
            lexer.Lexer(rules)


class LexerTokenizerTest(unittest.TestCase):

    def test_parse_arithmetic(self):
        l = lexer.Lexer(r'''
            WS         r"\s+"
            Number     r'[0-9]+(\.[0-9]*)?'
            Operator   r'\+|\-|\*|\/'
        ''')
        tokens = list(l.tokenize('5   + 7.5'))
        self.assertEqual([token.value for token in tokens], ['5', '   ', '+', ' ', '7.5'])
        self.assertEqual([token.token_id for token in tokens], ['Number', 'WS', 'Operator', 'WS', 'Number'])

    def test_parse_with_emit_false(self):
        l = lexer.Lexer(r'''
            WS[emit=false]   r'\s+'
            Identifier   r'[a-zA-Z][a-zA-Z0-9_]*'
            Arrow        '->'
        ''')
        tokens = list(l.tokenize('Root   ->   Foo Bar Baz'))
        # Whitespace is not emitted.
        self.assertEqual([token.value for token in tokens], ['Root', '->', 'Foo', 'Bar', 'Baz'])


if __name__ == '__main__':
    unittest.main()
