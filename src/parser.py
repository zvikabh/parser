"""LL(1) context-free grammar parser. Parses an input into an abstract syntax tree."""

from __future__ import annotations
import collections
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
            raise ParserError("Expecting at least one production in the grammar")
        if "ROOT" not in self.productions_by_left_id:
            raise ParserError("Grammar must have a `ROOT` node")

    @functools.cached_property
    def nonterminals(self) -> list[str]:
        return list(self.productions_by_left_id.keys())

    @functools.cached_property
    def terminals(self) -> list[str]:
        all_terms = set[str]()
        for prod in self.productions_by_left_id.values():
            for deriv in prod.derivations:
                for term in deriv.terms:
                    all_terms.add(term)
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
        for i, deriv1 in enumerate(self.derivations):
            for deriv2 in self.derivations[i+1:]:
                if deriv1 == deriv2:
                    raise ParserError(f"Duplicate derivation {deriv1} in production {self.left_id}")

    def __str__(self) -> str:
        s = f"{self.left_id} -> {self.derivations[0]}"
        for deriv in self.derivations[1:]:
            s += f"\n    | {deriv}"
        return s + " ;"


@dataclasses.dataclass(frozen=True)
class Derivation:
    terms: tuple[str, ...]

    def __str__(self) -> str:
        if not self.terms:
            return 'ε'
        return ' '.join(self.terms)


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

    Implementation note: During grammar parsing, terms followed by a question mark are converted to a production rule
    of the form `Term? -> empty | Term`. The resulting grammar does not support question marks. Question marks are not
    allowed as part of identifier strings, so there is no risk of collision with existing identifier strings.
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

        # Add production rules for all optional identifiers.
        # Support for optional identifiers is implemented by adding a production rule of the type
        #   `Identifier? -> empty | Identifier`
        # for all identifiers which appear with a `?` somewhere in the grammar.
        all_optional_ids = set[str]()
        for prod in productions_by_left_id.values():
            for deriv in prod.derivations:
                for term in deriv.terms:
                    if term[-1] == '?':
                        all_optional_ids.add(term[:-1])
        for optional_id in all_optional_ids:
            productions_by_left_id[optional_id + '?'] = Production(
                left_id=optional_id + '?',
                derivations=[
                    Derivation(()),
                    Derivation((optional_id,))
                ]
            )

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
        return Derivation(terms=tuple(terms))

    def parse_Term(self) -> str:
        identifier = self.consume('IDENTIFIER').value
        is_optional = (self.cur_token.token_id == 'QUESTION_MARK')
        if is_optional:
            self.consume('QUESTION_MARK')
            identifier += '?'
        return identifier


class _ParsingTable:
    """A parsing table for a given LL(1) grammar.

    The entry at parsing_table[nonterminal, terminal] can be either:
    - `None`, if `terminal` is not allowed when starting to parse `nonterminal`.
    - One of the derivations in one of the productions in the grammar, indicating that this derivation is the one to be
      produced when encountering `terminal` while starting to parse `nonterminal`.

    The specified grammar is LL(1) if and only if it can be converted to such a parsing table.
    An exception is raised when building the _ParsingTable object if the input grammar is not LL(1).

    Attributes:
        grammar: The grammar for which the parsing table is built.
        first_terminals_for_nonterminal: Maps from nonterminal id to the set of terminals which could be the first
            terminal in a production of the nonterminal.
            If the nonterminal may be parsed as ε, the value will include None.
        first_terminals_for_deriv: Maps from nonterminal and one of its derivations to the set of terminals which could
            be the first terminal in a production of that derivation.
            If the derivation may be parsed as ε, the value will include None.
        follow_terminals: Map from nonterminal id to the set of terminals which could follow immediately after parsing
            that nonterminal.
            If the nonterminal can be the last nonterminal in a valid derivation, the value will include None.
        _table: Map from (current_nonterminal, next_terminal) to a Derivation. If we are currently starting to parse
            `current_nonterminal`, and the next token to be parsed is `next_terminal`, then the returned derivation is
            the parsing rule which matches it. If no possible derivation matches this situation, the table will have
            no entry in this position. The definition of an LL(1) grammar is that this table contains no more than one
            derivation in every cell.
    """

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.first_terminals_for_nonterminal : dict[str, set[str | None]] = {}
        self.first_terminals_for_deriv: dict[str, dict[Derivation, set[str | None]]] = {}
        for nonterminal in self.grammar.nonterminals:
            self._find_first_terminals_for_nonterminal(nonterminal)
        self.follow_terminals = self._find_follow_terminals()
        self._table = self._build_parsing_table()

    def _find_first_terminals_for_nonterminal(
            self, nonterminal: str, recursion_path: list[tuple[str, Derivation]] | None = None
    ) -> set[str | None]:
        """Returns all possible values that may appear as the first terminal in a production of `nonterminal`.

        If `nonterminal` may be parsed as ε, the output will include None.

        Along the way, if self.first_terminals_for_deriv has not been computed yet, calculates that as well.
        """
        if nonterminal in self.first_terminals_for_nonterminal:
            return self.first_terminals_for_nonterminal[nonterminal]

        # Check for loops in the recursion
        recursion_path = recursion_path or []
        for i, (prev_nonterm, prev_deriv) in enumerate(recursion_path):
            if prev_nonterm == nonterminal:
                # Found loop, build error message.
                cycle = []
                for loop_nonterm, loop_deriv in recursion_path[i:]:
                    cycle.append(f'{loop_nonterm} -> {loop_deriv} ;')
                cycle.append(f'{prev_nonterm} -> {prev_deriv} ;')
                raise ParserError(f"Infinite left-recursion in grammar:\n{'\n'.join(cycle)}")

        # Not a loop, and not computed yet. Compute possible first terminals.
        first_terminals = set[str | None]()
        first_terminals_for_deriv = dict[Derivation, set[str | None]]()
        for deriv in self.grammar.productions_by_left_id[nonterminal].derivations:
            first_terminals_for_deriv[deriv] = set[str | None]()
            if not deriv.terms:
                first_terminals.add(None)
                first_terminals_for_deriv[deriv].add(None)
            elif deriv.terms[0] in self.grammar.terminals:
                first_terminals.add(deriv.terms[0])
                first_terminals_for_deriv[deriv].add(deriv.terms[0])
            else:
                recursion_path.append((nonterminal, deriv))
                first_terms_for_cur_deriv = self._find_first_terminals_for_nonterminal(deriv.terms[0], recursion_path)
                first_terminals |= first_terms_for_cur_deriv
                first_terminals_for_deriv[deriv] |= first_terms_for_cur_deriv
                recursion_path.pop()

        self.first_terminals_for_nonterminal[nonterminal] = first_terminals
        self.first_terminals_for_deriv[nonterminal] = first_terminals_for_deriv
        return first_terminals

    def _find_follow_terminals(self) -> dict[str, set[str | None]]:
        """Builds a map from nonterminal id to the set of all terminals which could follow it."""
        follow_terminals = {nonterm: set[str | None]() for nonterm in self.grammar.nonterminals}
        follow_terminals['ROOT'] = {None}

        # Map from nonterminal to derivations containing it.
        # Each entry in the value contains the production_id, derivation, and index in the derivation pointing to the
        # nonterminal.
        nonterm_to_deriv = collections.defaultdict(list[tuple[str, Derivation, int]])
        for prod_id, prod in self.grammar.productions_by_left_id.items():
            for deriv in prod.derivations:
                for pos, term in enumerate(deriv.terms):
                    if term in self.grammar.nonterminals:
                        nonterm_to_deriv[term].append((prod_id, deriv, pos))

        found_change = True
        # Repeat the loop until no more changes found.
        # Guaranteed to terminate because if changes were found, this means that some terminal was added to one of the
        # entries in `follow_terminals`, and there is a finite number of terminals which can be added.
        while found_change:
            found_change = False
            for nonterm in self.grammar.nonterminals:
                curr_follow = follow_terminals[nonterm]
                for prod_id, deriv, pos in nonterm_to_deriv[nonterm]:
                    if pos == len(deriv.terms) - 1:
                        # `nonterm` is the last term in the derivation. Add FOLLOW(prod_id) to curr_follow.
                        found_change = _extend_set(curr_follow, follow_terminals[prod_id]) or found_change
                    else:
                        next_term = deriv.terms[pos + 1]
                        if next_term in self.grammar.terminals:
                            # `non_term` can be followed by the terminal `next_term`.
                            found_change = _extend_set(curr_follow, {next_term}) or found_change
                        else:
                            # `non_term` can be followed by FIRST(next_term).
                            found_change = _extend_set(curr_follow, self.first_terminals_for_nonterminal[next_term]) or found_change

                        # Check whether deriv.terms[pos+1:] (all the way to the end) could all be empty.
                        # If so, we need to also add follow_terminals[prod_id].
                        can_be_empty = []
                        for t in deriv.terms[pos+1:]:
                            can_be_empty.append(t in self.grammar.nonterminals and None in self.first_terminals_for_nonterminal[t])
                        if all(can_be_empty):
                            found_change = _extend_set(curr_follow, follow_terminals[prod_id]) or found_change

        return follow_terminals

    def _build_parsing_table(self) -> dict[tuple[str, str], Derivation | None]:
        """Builds the parsing table returned by self[nonterminal, terminal]."""
        for nonterm, production in self.grammar.productions_by_left_id.items():
            for deriv in production.derivations:
                pass # TODO

    def __getitem__(self, item: tuple[str, str]) -> Derivation | None:
        """The derivation to be produced if the current nonterminal is item[0] and the next terminal is item[1].

        Raises ParserError if this is not a legal combination in the given grammar.
        """
        nonterminal, terminal = item
        try:
            return self._table[nonterminal, terminal]
        except KeyError:
            raise ParserError(f'The terminal {terminal} is not allowed to start a derivation of {nonterminal}')


def _extend_set(target_set: set, to_add: set) -> bool:
    """Add the items in `to_add` to the set `target_set`. Returns True if at least one new item was added."""
    # added = False
    # for item in to_add:
    #     if item not in target_set:
    #         target_set.add(item)
    #         print(f'Added {item}')
    #         added = True
    # return added
    original_size = len(target_set)
    target_set.update(to_add)
    return len(target_set) > original_size


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
