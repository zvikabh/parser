import unittest

import parser


class ParseGrammarTest(unittest.TestCase):

    def test_simple_grammar(self):
        grammar_str = """
            ROOT -> Sum;
            Sum  -> NUMBER PLUS NUMBER
                  | NUMBER MINUS NUMBER ;
        """
        grammar = parser._parse_grammar(grammar_str)
        self.assertEqual(2, len(grammar.productions))
        self.assertEqual(str(grammar.productions[0]), "ROOT -> Sum ;")
        self.assertEqual(str(grammar.productions[1]), "Sum -> NUMBER PLUS NUMBER\n    | NUMBER MINUS NUMBER ;")

    def test_grammar_with_optional(self):
        grammar_str = """
            ROOT -> LITERAL ROOT?;
        """
        grammar = parser._parse_grammar(grammar_str)
        self.assertEqual(str(grammar), "ROOT -> LITERAL ROOT? ;")

    def test_grammar_missing_semicolon(self):
        grammar_str = """
            ROOT -> LITERAL ROOT?
        """
        with self.assertRaisesRegex(parser.ParserError, "expected SEMICOLON"):
            grammar = parser._parse_grammar(grammar_str)

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


if __name__ == '__main__':
    unittest.main()
