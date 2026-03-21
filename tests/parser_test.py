import unittest

import lexer
import parser


class SimpleParserTest(unittest.TestCase):

    def setUp(self) -> None:
        rules = r'''
            WHITESPACE[emit=false]  r'\s+'
            INTEGER                  '[0-9]+'
            OPERATOR                r'[+\-]'
        '''
        self.lexer = lexer.Lexer(rules)

    def test_simple(self) -> None:
        grammar_str = """
            ROOT -> Sum;
            Sum  -> INTEGER OPERATOR INTEGER ;
        """
        p = parser.Parser(self.lexer, grammar_str)
        ast = p.parse('5 + 6')
        self.assertEqual(ast.pretty_print(), """\
ROOT
  Sum
    '5'
    '+'
    '6'
""")

    def test_arithmetic_expr(self) -> None:
        grammar_str = '''
            ROOT -> Expr ;
            Expr -> INTEGER MoreTerms? ;
            MoreTerms -> OPERATOR Expr ;
        '''
        p = parser.Parser(self.lexer, grammar_str)
        ast = p.parse('10 + 6 - 3')
        self.assertEqual(ast.pretty_print(), """\
ROOT
  Expr
    '10'
    MoreTerms
      '+'
      Expr
        '6'
        MoreTerms
          '-'
          Expr
            '3'
            MoreTerms?
""")

    def test_invalid_artihmetic_expr(self) -> None:
        grammar_str = '''
            ROOT -> Expr ;
            Expr -> INTEGER MoreTerms? ;
            MoreTerms -> OPERATOR Expr ;
        '''
        p = parser.Parser(self.lexer, grammar_str)
        with self.assertRaisesRegex(parser.ParserError,
                                    r'The terminal \$ is not allowed to start a derivation of Expr'):
            p.parse('10 + 6 -')

    def test_invalid_artihmetic_expr_2(self) -> None:
        grammar_str = '''
            ROOT -> Expr ;
            Expr -> INTEGER MoreTerms? ;
            MoreTerms -> OPERATOR Expr ;
        '''
        p = parser.Parser(self.lexer, grammar_str)
        with self.assertRaisesRegex(parser.ParserError,
                                    r'The terminal INTEGER is not allowed to start a derivation of MoreTerms\?'):
            p.parse('10 6 -')


class EquationParserTest(unittest.TestCase):

    def setUp(self) -> None:
        rules = r'''
            WHITESPACE[emit=false]  r'[ \t]+'
            INTEGER                  '[0-9]+'
            SIGN                    r'[+\-]'
            VARNAME                  '[A-Za-z]+'
            EQUALS                   '='
            NEWLINE                 r'\n'
        '''
        self.lexer = lexer.Lexer(rules)
        grammar_str = '''
            ROOT -> EqSystem ;
            EqSystem -> Eq MoreEqs? ;
            MoreEqs -> NEWLINE Eq MoreEqs? ;
            Eq -> Expr EQUALS Expr ;
            Expr -> FirstTerm OtherTerms? ;
            FirstTerm -> SIGN? ActualTerm ;
            ActualTerm -> INTEGER VARNAME? | VARNAME ;
            OtherTerms -> SIGN ActualTerm OtherTerms? ;
        '''
        self.parser = parser.Parser(self.lexer, grammar_str)

    def test_single_equation(self) -> None:
        ast = self.parser.parse('5x+8y=3')
        self.assertEqual(ast.pretty_print(), '''\
ROOT
  EqSystem
    Eq
      Expr
        FirstTerm
          SIGN?
          ActualTerm
            '5'
            'x'
        OtherTerms
          '+'
          ActualTerm
            '8'
            'y'
          OtherTerms?
      '='
      Expr
        FirstTerm
          SIGN?
          ActualTerm
            '3'
            VARNAME?
        OtherTerms?
    MoreEqs?
''')

    def test_equation_set(self) -> None:
        ast = self.parser.parse('5x+8y=3\n-x+2y=-3')
        self.assertEqual(ast.pretty_print(), '''\
ROOT
  EqSystem
    Eq
      Expr
        FirstTerm
          SIGN?
          ActualTerm
            '5'
            'x'
        OtherTerms
          '+'
          ActualTerm
            '8'
            'y'
          OtherTerms?
      '='
      Expr
        FirstTerm
          SIGN?
          ActualTerm
            '3'
            VARNAME?
        OtherTerms?
    MoreEqs
      '\\n'
      Eq
        Expr
          FirstTerm
            '-'
            ActualTerm
              'x'
          OtherTerms
            '+'
            ActualTerm
              '2'
              'y'
            OtherTerms?
        '='
        Expr
          FirstTerm
            '-'
            ActualTerm
              '3'
              VARNAME?
          OtherTerms?
      MoreEqs?
''')

    def test_invalid_equation_1(self) -> None:
        with self.assertRaisesRegex(parser.ParserError,
                                    'The terminal SIGN is not allowed to start a derivation of ActualTerm'):
            self.parser.parse('5x++y=3')

    def test_invalid_equation_2(self) -> None:
        with self.assertRaisesRegex(parser.ParserError,
                                    r"Expected token of type EQUALS, got token '<end of input>' of type \$"):
            self.parser.parse('5x+y')


if __name__ == '__main__':
    unittest.main()
