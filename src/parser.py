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
WHITESPACE[emit=false]    r'[\s\n]+'
ARROW                     r'\->'
VBAR                      r'\|'
QUESTION_MARK             r'\?'
SEMICOLON                 ';'
IDENTIFIER                '[a-zA-Z][a-zA-Z0-9_]*'
'''


@dataclasses.dataclass(frozen=True)
class Grammar:
    """AST of the user-specified grammar."""
    productions: list[Production]

    def __post_init__(self):
        if not self.productions:
            raise ParserError(f"Expecting at least one production in the grammar")
        left_ids = {prod.left_id for prod in self.productions}
        if len(left_ids) != len(self.productions):
            raise ParserError(f"Duplicate production ids in grammar")

    def __str__(self) -> str:
        return "\n".join(str(prod) for prod in self.productions)


@dataclasses.dataclass(frozen=True)
class Production:
    left_id: str
    derivations: list[Derivation]

    def __post_init__(self):
        if not self.derivations:
            raise ParserError(f"Expecting at least one derivation in production {self.left_id}")

    def __str__(self) -> str:
        s = f"{self.left_id} -> {self.derivations[0]}"
        for deriv in self.derivations[1:]:
            s += f"\n    | {deriv}"
        return s + " ;"


@dataclasses.dataclass(frozen=True)
class Derivation:
    terms: list[Term]

    def __str__(self) -> str:
        return ' '.join(str(term) for term in self.terms)


@dataclasses.dataclass(frozen=True)
class Term:
    id: str
    is_optional: bool  # Indicates whether this term is followed by a question mark.

    def __str__(self) -> str:
        if self.is_optional:
            return self.id + "?"
        return self.id


def _parse_grammar(grammar: str) -> Grammar:
    grammar_lexer = lexer.Lexer(_GRAMMAR_LEXER)
    try:
        tokens = list(grammar_lexer.tokenize(grammar))
    except lexer.LexerError as e:
        raise ParserError("Failed to parse grammar") from e

    grammar_parser = _GrammarParser(tokens)
    return grammar_parser.parse_ROOT()


class _GrammarParser:
    """A parser for the grammar rules.

    The grammar for the grammar is defined formally as follows. For a simpler explanation and examples, see
    the Parser docstring.
    ROOT           -> Productions ;
    Productions    -> Production Productions? ;
    Production     -> IDENTIFIER ARROW Derivation AltDerivations? SEMICOLON ;
    AltDerivations -> VBAR Derivation AltDerivations? ;
    Derivation     -> Term Derivation? ;
    Term           -> IDENTIFIER QUESTION_MARK? ;
    """

    def __init__(self, tokens: list[lexer.Token]) -> None:
        self.tokens = tokens
        self.cur_pos = 0

    @property
    def cur_token(self) -> lexer.Token:
        if self.at_eof:
            return lexer.Token(token_id='EOF', value='EOF', pos_start=self.cur_pos, pos_end=self.cur_pos)
        return self.tokens[self.cur_pos]

    @property
    def at_eof(self) -> bool:
        return self.cur_pos == len(self.tokens)

    def consume(self, token_id: str) -> lexer.Token:
        if self.cur_token.token_id != token_id:
            raise ParserError(
                f"Error parsing grammar: Unexpected token '{self.cur_token}' (expected {token_id})"
            )
        token = self.cur_token
        self.cur_pos += 1
        return token

    def parse_ROOT(self) -> Grammar:
        return Grammar(productions=self.parse_Productions())

    def parse_Productions(self) -> list[Production]:
        production = self.parse_Production()
        if self.at_eof:
            return [production]
        return [production] + self.parse_Productions()

    def parse_Production(self) -> Production:
        left_id = self.consume('IDENTIFIER').value
        self.consume('ARROW')
        derivations = [self.parse_Derivation()]
        while self.cur_token.token_id == 'VBAR':
            self.consume('VBAR')
            derivations.append(self.parse_Derivation())
        self.consume('SEMICOLON')
        return Production(left_id=left_id, derivations=derivations)

    def parse_Derivation(self) -> Derivation:
        terms = [self.parse_Term()]
        while self.cur_token.token_id == 'IDENTIFIER':
            terms.append(self.parse_Term())
        return Derivation(terms=terms)

    def parse_Term(self) -> Term:
        identifier = self.consume('IDENTIFIER').value
        is_optional = (self.cur_token.token_id == 'QUESTION_MARK')
        if is_optional:
            self.consume('QUESTION_MARK')
        return Term(id=identifier, is_optional=is_optional)


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

    For the formal definition of the grammar for defining grammars, see _GrammarParser.
    """

    def __init__(self, lex: lexer.Lexer, grammar: str) -> None:
        self.lexer = lex
        self.grammar = _parse_grammar(grammar)
