"""LL(1) context-free grammar parser. Parses an input into an abstract syntax tree."""

from __future__ import annotations
import dataclasses
import functools

import lexer
from lexer import Lexer


class ParserError(Exception):
    """Raised when the parser encounters ungrammatical input."""


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
    productions_by_left_id: dict[str, Production]

    def __post_init__(self):
        if not self.productions_by_left_id:
            raise ParserError(f"Expecting at least one production in the grammar")

    @functools.cached_property
    def nonterminals(self) -> list[str]:
        return list(self.productions_by_left_id.keys())

    @functools.cached_property
    def terminals(self) -> list[str]:
        all_terms = set[str]()
        for prod in self.productions_by_left_id.values():
            for deriv in prod.derivations:
                for term in deriv.terms:
                    all_terms.add(term.id)
        nonterminals = set(self.nonterminals)
        return list(all_terms - nonterminals)

    def __str__(self) -> str:
        return "\n".join(str(prod) for prod in self.productions_by_left_id.values())


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


def _ensure_grammar_lexer_consistency(lex: Lexer, grammar: Grammar):
    token_ids_set = set(lex.emitted_token_ids)
    terminals_set = set(grammar.terminals)
    if orphaned_lexer_tokens := token_ids_set - terminals_set:
        raise ParserError(
            f"The token(s) [{', '.join(orphaned_lexer_tokens)}] are defined by the lexer, but never referenced "
            f"by the grammar. Consider adding [emit=false] to prevent them from reaching the parser."
        )
    if orphaned_terminals := terminals_set - token_ids_set:
        raise ParserError(
            f"The terminal(s) [{', '.join(orphaned_terminals)}] are mentioned on the right side of productions, "
            f"but they do not appear either in the left side of productions or as lexer terminals."
        )


class _GrammarParser:
    """A parser for the grammar rules.

    The grammar for the grammar is defined formally as follows. For a simpler explanation and examples, see
    the Parser docstring.
    ROOT           -> Productions ;
    Productions    -> Production Productions? ;
    Production     -> IDENTIFIER ARROW Derivation AltDerivations? SEMICOLON ;
    AltDerivations -> VBAR Derivation AltDerivations? ;
    Derivation     -> empty | Term Derivation? ;
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
        productions = self.parse_Productions()
        productions_by_left_id = {}
        for prod in productions:
            if prod.left_id in productions_by_left_id:
                raise ParserError(f"Production '{prod.left_id}' appears twice in the grammar")
            productions_by_left_id[prod.left_id] = prod
        return Grammar(productions_by_left_id)

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
        terms = []
        while self.cur_token.token_id == 'IDENTIFIER':
            terms.append(self.parse_Term())
        return Derivation(terms=terms)

    def parse_Term(self) -> Term:
        identifier = self.consume('IDENTIFIER').value
        is_optional = (self.cur_token.token_id == 'QUESTION_MARK')
        if is_optional:
            self.consume('QUESTION_MARK')
        return Term(id=identifier, is_optional=is_optional)


class _ParsingTable:
    """A parsing table for a given LL(1) grammar.

    The entry at parsing_table[nonterminal, terminal] can be either:
    - `None`, if `terminal` is not allowed when starting to parse `nonterminal`.
    - One of the derivations in one of the productions in the grammar, indicating that this derivation is the one to be
      produced when encountering `terminal` while starting to parse `nonterminal`.

    The specified grammar is LL(1) if and only if it can be converted to such a parsing table.
    An exception is raised when building the _ParsingTable object if the input grammar is not LL(1).
    """

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.table = self._build_parsing_table()

    def _build_parsing_table(self) -> dict[tuple[str, str], Derivation]:
        pass  # TODO



@dataclasses.dataclass(frozen=True)
class Node:
    children: list[Node]
    token: lexer.Token | None = None  # Only for terminal nodes


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
        _ensure_grammar_lexer_consistency(lex, self.grammar)
        self.parsing_table = _ParsingTable(self.grammar)

    def parse(self, input: str) -> Node:
        pass  # TODO
