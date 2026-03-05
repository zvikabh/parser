"""Lexical analyzer. Parses an input string into tokens."""

import ast
import dataclasses
import re
from typing import Iterator


class LexerError(Exception):
    """Raised when the lexer encounters invalid input."""


@dataclasses.dataclass(frozen=True)
class Token:
    id: str
    regexp: re.Pattern


class Lexer:
    r"""Lexical analyzer. Parses an input string into tokens.

    The input consists of a sequence of lines, each defining a token.
    A token is defined by its identifier (a valid Python identifier) and its matching rule (a regexp enclosed in quotes
    or r'' quotes, with ordinary Python escaping).
    The token identifier is separated from the matching rule by whitespace.
    Tokens are matched in the order appearing in the file (earlier tokens getting higher precedence).
    Whitespace before the identifier and after the matching rule is ignored.
    Whitespace-only lines are ignored.
    Anything preceded by '#' is considered a comment and ignored.

    Example:
    Whitespace  r'\s+'
    Float       r'[0-9]\.[0-9]*'
    Integer     '[0-9]+'  # Only matches if Float did not match
    String      '"[^"]*"'
    Identifier  '[a-zA-Z][a-zA-Z0-9_]*'
    """

    def __init__(self, lexer_def: str):
        self._tokens: list[Token] = []
        for n_line, line in enumerate(lexer_def.split('\n')):
            line = line.strip()
            if not line: continue
            if line[0] == '#': continue
            m = re.match(r'([a-zA-Z][a-zA-Z0-9_]*)\s+(.+)$', line)
            if not m:
                raise LexerError(f'Invalid token identifier or matching rule in line {n_line + 1}')
            token_id = m.group(1)
            try:
                parsed_matching_rule = ast.parse(m.group(2))
                assert len(parsed_matching_rule.body) == 1, 'Matching rule must contain a single string'
                assert isinstance(parsed_matching_rule.body[0], ast.Expr), (
                    'Matching rule must be a valid Python expression')
                assert isinstance(parsed_matching_rule.body[0].value, ast.Constant), (
                    'Matching rule must be a valid Python constant')
                matching_rule = parsed_matching_rule.body[0].value.value
                assert isinstance(matching_rule, str), 'Matching rule must be a quote-enclosed string'
                matching_rule = re.compile(matching_rule)
            except (SyntaxError, ValueError, AssertionError, re.PatternError) as e:
                raise LexerError(f'Invalid matching rule in line {n_line + 1}') from e
            self._tokens.append(Token(id=token_id, regexp=matching_rule))

    def tokenize(self, input: str) -> Iterator[Token]:
        pass  # TODO