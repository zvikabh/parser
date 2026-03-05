import unittest

import lexer


class CreateLexerTest(unittest.TestCase):

    def test_create_lexer_happy_flow(self):
        rules = r'''
            # Example comment
            Whitespace  r'\s+'
            
            Float       r'[0-9]\.[0-9]*'
            Integer     '[0-9]+'  # Only matches if Float did not match
            String      '"[^"]*"'
            Identifier  '[a-zA-Z][a-zA-Z0-9_]*'
        '''
        l = lexer.Lexer(rules)
        expected_ids = ['Whitespace', 'Float', 'Integer', 'String', 'Identifier']
        actual_ids = [token.id for token in l._tokens]
        self.assertEqual(expected_ids, actual_ids)

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


if __name__ == '__main__':
    unittest.main()
