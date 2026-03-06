"""LL(1) context-free grammar parser. Parses an input into an abstract syntax tree."""

from __future__ import annotations
import dataclasses

import lexer


class ParserError(Exception):
    """Raised when the parser encounters ungrammatical input."""


@dataclasses.dataclass(frozen=True)
class Node:
    children: list[Node]
    token: lexer.Token | None = None  # Only for terminal nodes


# Lexer definition for the input grammar definition.
_GRAMMAR_LEXER = r'''
COMMENT[emit=false]       r'#(\s)*'
WHITESPACE[emit=false]    r'(\s\n)+'
ARROW                     r'\->'
OR                        '|'
QUESTION_MARK             r'\?'
SEMICOLON                 ';'
IDENTIFIER                '[a-zA-Z][a-zA-Z0-9_]*'
'''


class Parser:
    r"""LL(1) context-free grammar parser. Parses an input into an abstract syntax tree.

    The input is fed into the provided lexer, and then parsed with a grammar having the following syntax:

    ROOT       -> Equation ;  # Anything after '#' is a comment.
    Equation   -> Side EQUALS_SIGN Side ;
    Side       -> FirstTerm OtherTerms? ;
    FirstTerm  -> ActualTerm
                | Sign ActualTerm ;
    OtherTerms -> Sign ActualTerm OtherTerms? ;
    ActualTerm -> INTEGER VAR_NAME?
                | VAR_NAME ;
    Sign       -> PLUS | MINUS ;

    All values on the right-hand side must be either productions defined in the grammar, or token ids provided by the
    lexer. By convention, the token ids are all-caps.

    The root node must be called ROOT. Whitespace and newlines are ignored.

    More formally, the grammar for the grammar is defined as:
    ROOT           -> Productions ;
    Productions    -> Production Productions? ;
    Production     -> IDENTIFIER ARROW Derivation AltDerivations? SEMICOLON ;
    AltDerivations -> OR Derivation AltDerivations? ;
    Derivation     -> Term Derivation? ;
    Term           -> IDENTIFIER QUESTION_MARK? ;
    """

    def __init__(self, lex: lexer.Lexer, grammar: str):
        self.lexer = lex
        grammar_lexer = lexer.Lexer(_GRAMMAR_LEXER)
        try:
            self.grammar = list(grammar_lexer.tokenize(grammar))
        except lexer.LexerError as e:
            raise ParserError("Failed to parse grammar") from e
        # HERE: Parse grammar...
