import unittest

import lexer
import parser


class ParseGrammarTest(unittest.TestCase):

    def test_simple_grammar(self):
        grammar_str = """
            ROOT -> Sum;
            Sum  -> NUMBER PLUS NUMBER
                  | NUMBER MINUS NUMBER ;
        """
        grammar = parser._parse_grammar(grammar_str)
        self.assertEqual(2, len(grammar.productions_by_left_id))
        self.assertEqual(str(grammar.productions_by_left_id["ROOT"]), "ROOT -> Sum ;")
        self.assertEqual(
            str(grammar.productions_by_left_id["Sum"]),
            "Sum -> NUMBER PLUS NUMBER\n    | NUMBER MINUS NUMBER ;"
        )

    def test_grammar_with_optional(self):
        grammar_str = """
            ROOT -> LITERAL ROOT?;
            LITERAL -> LETTER ROOT?;
        """
        grammar = parser._parse_grammar(grammar_str)
        self.assertEqual(str(grammar), """
ROOT -> LITERAL ROOT? ;
LITERAL -> LETTER ROOT? ;
ROOT? -> ε\n    | ROOT ;""".strip())

    def test_grammar_missing_semicolon(self):
        grammar_str = """
            ROOT -> LITERAL ROOT?
        """
        with self.assertRaisesRegex(parser.ParserError, "expected SEMICOLON"):
            parser._parse_grammar(grammar_str)

    def test_grammar_missing_arrow(self):
        grammar_str = """
            ROOT to LITERAL ROOT?
        """
        with self.assertRaisesRegex(parser.ParserError, "expected ARROW"):
            parser._parse_grammar(grammar_str)

    def test_grammar_invalid_character(self):
        grammar_str = """
            ROOT -> Real-Number Operator Real-Number;
        """
        with self.assertRaisesRegex(parser.ParserError, "Failed to parse grammar"):
            parser._parse_grammar(grammar_str)


class EnsureGrammarLexerConsistencyTest(unittest.TestCase):

    def setUp(self):
        self.lex = lexer.Lexer(r'''
            WS[emit=false]    r"\s+"
            Number            r'[0-9]+(\.[0-9]*)?'
            Operator          r'\+|\-|\*|\/'
        ''')

    def test_happy_flow(self):
        grammar_str = '''
            ROOT -> Number Operator Number;
        '''
        grammar = parser._parse_grammar(grammar_str)
        parser._ensure_grammar_lexer_consistency(self.lex, grammar)

    def test_orphaned_token(self):
        grammar_str = '''
            ROOT -> Operator;
        '''
        grammar = parser._parse_grammar(grammar_str)
        with self.assertRaisesRegex(
                parser.ParserError,
                r"The token\(s\) \[Number\] are defined by the lexer, but never referenced by the grammar."
        ):
            parser._ensure_grammar_lexer_consistency(self.lex, grammar)

    def test_orphaned_terminal(self):
        grammar_str = '''
            ROOT -> Number Operator Number
                  | Sign Number;
        '''
        grammar = parser._parse_grammar(grammar_str)
        with self.assertRaisesRegex(
                parser.ParserError,
                r"The terminal\(s\) \[Sign\] are mentioned on the right side of productions"
        ):
            parser._ensure_grammar_lexer_consistency(self.lex, grammar)


if __name__ == '__main__':
    unittest.main()
