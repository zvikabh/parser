"""Interpreter for a simple version of the BASIC programming language."""
from __future__ import annotations
import dataclasses
import sys
from typing import cast, Any, Callable, Iterable

import lexer
import parser


class BasicError(Exception):
    """Runtime error in the input program."""


LEXER_RULES = r'''
    STRING_LITERAL                 r'"[^"]*"'
    WHITESPACE[emit=false]         r'\s+'
    FLOAT_CONST                    r'([0-9]+\.[0-9]*)|(\.[0-9]+)'
    INTEGER_CONST                  r'[0-9]+'
    PREC_0_OPERATOR                r'\*\*'
    PREC_1_OPERATOR                r'\*|\/'
    PREC_2_OPERATOR                r'\-|\+'
    PREC_3_OPERATOR                r'[<>](=)?'
    LEFT_PAREN                     r'\('
    RIGHT_PAREN                    r'\)'
    EQUALS                         r'='
    GOTO[ignore_case=true]         r'GOTO\b'
    PRINT[ignore_case=true]        r'PRINT\b'
    IF[ignore_case=true]           r'IF\b'
    THEN[ignore_case=true]         r'THEN\b'
    ELSE[ignore_case=true]         r'ELSE\b'
    ENDIF[ignore_case=true]        r'END\s+IF\b'
    IDENTIFIER[to_upper=true]      r'[A-Za-z][A-Za-z0-9_]*'
'''


GRAMMAR = '''
    ROOT             -> Statement ROOT?;
    Statement        -> LineNumber? ActualStatement;
    LineNumber       -> INTEGER_CONST;
    ActualStatement  -> Assignment
                      | GotoStatement
                      | PrintStatement
                      | IfStatement;
    Assignment       -> IDENTIFIER EQUALS Expr;
    GotoStatement    -> GOTO LineNumber;
    PrintStatement   -> PRINT Expr;
    IfStatement      -> IF Expr THEN ROOT ElseClause? ENDIF;
    ElseClause       -> ELSE ROOT;
    Expr             -> Expr3 MoreExpr?;
    MoreExpr         -> PREC_3_OPERATOR Expr
                      | EQUALS Expr;
    Expr3            -> Expr2 MoreExpr3?;
    MoreExpr3        -> PREC_2_OPERATOR Expr3;
    Expr2            -> Expr1 MoreExpr2?;
    MoreExpr2        -> PREC_1_OPERATOR Expr2;
    Expr1            -> Expr0 MoreExpr1?;
    MoreExpr1        -> PREC_0_OPERATOR Expr1;
    Expr0            -> Literal
                      | PREC_2_OPERATOR Literal 
                      | LEFT_PAREN Expr RIGHT_PAREN 
                      | IDENTIFIER;
    Literal          -> FLOAT_CONST
                      | INTEGER_CONST
                      | STRING_LITERAL;
'''


OPERATOR_FUNCS = {
    '**': lambda x, y: x**y,
    '*': lambda x, y: x*y,
    '/': lambda x, y: x/y,
    '+': lambda x, y: x+y,
    '-': lambda x, y: x-y,
    '=': lambda x, y: x==y,
    '>': lambda x, y: x>y,
    '<': lambda x, y: x<y,
    '>=': lambda x, y: x>=y,
    '<=': lambda x, y: x<=y,
}


def cast_ntn(node: parser.Node) -> parser.NonterminalNode:
    assert isinstance(node, parser.NonterminalNode)
    return node


def cast_tn(node: parser.Node) -> parser.TerminalNode:
    assert isinstance(node, parser.TerminalNode)
    return node


@dataclasses.dataclass
class Statement:
    """Base class for all statement types."""
    line_number: int | None

    def exec(self, interpreter: BasicInterpreter) -> Iterable[str]:
        raise NotImplementedError()


@dataclasses.dataclass
class AssignmentStatement(Statement):
    identifier: str
    expr: parser.NonterminalNode

    def __post_init__(self) -> None:
        assert self.expr.prod_id == 'Expr'

    def exec(self, interpreter: BasicInterpreter) -> Iterable[str]:
        interpreter.variables[self.identifier] = interpreter.evaluate_expr(self.expr)
        interpreter.cur_statement += 1
        yield from []  # To make Python recognize this as a generator

    def __str__(self) -> str:
        return f'{self.identifier} = {self.expr.children[0]}'


@dataclasses.dataclass
class GotoStatement(Statement):
    target_line: int

    def exec(self, interpreter: BasicInterpreter) -> Iterable[str]:
        if self.target_line not in interpreter.line_number_to_stmt_index:
            raise BasicError(f'GOTO specified an invalid target line number {self.target_line}')
        interpreter.cur_statement = interpreter.line_number_to_stmt_index[self.target_line]
        yield from []  # To make Python recognize this as a generator

    def __str__(self) -> str:
        return f'GOTO {self.target_line}'


@dataclasses.dataclass
class IfStatement(Statement):
    """A simplified IF statement, compiled from BASIC IF into essentially a JZ-like instruction.

    Attributes:
        condition: Node which will be evaluated to determine whether to jump.
        relative_jump: Relative number of statements to jump if the condition is FALSY.
            A value of 0 is the same as no-jump, causing the behavior to be identical regardless of the value of
            `condition`.
            A value of 1 will skip the next statement.
            A value of -1 will cause the If statement to be re-evalauted (likely resulting in an infinite loop).
    """
    condition: parser.NonterminalNode
    relative_jump_if_falsy: int

    def __post_init__(self) -> None:
        assert self.condition.prod_id == 'Expr'

    def exec(self, interpreter: BasicInterpreter) -> Iterable[str]:
        condition = interpreter.evaluate_expr(self.condition)
        if condition:
            interpreter.cur_statement += 1
        else:
            interpreter.cur_statement += self.relative_jump_if_falsy + 1
        yield from []

    def __str__(self) -> str:
        return f'TEST {self.condition.children[0]}\nJZ REL {self.relative_jump_if_falsy}'


@dataclasses.dataclass
class PrintStatement(Statement):
    expr: parser.NonterminalNode

    def __post_init__(self) -> None:
        assert self.expr.prod_id == 'Expr'

    def exec(self, interpreter: BasicInterpreter) -> Iterable[str]:
        interpreter.cur_statement += 1
        yield f'{interpreter.evaluate_expr(self.expr)}\n'

    def __str__(self) -> str:
        return f'PRINT {self.expr.children[0]}'


@dataclasses.dataclass
class RelativeJumpStatement(Statement):
    """An internal statement, used when compiling flow control statements.

    See `IfStatement` for definition and example uses of `relative_jump`.
    """
    relative_jump: int

    def exec(self, interpreter: BasicInterpreter) -> Iterable[str]:
        interpreter.cur_statement += self.relative_jump + 1
        yield from []

    def __str__(self) -> str:
        return f'RELJMP {self.relative_jump}'


def _node_to_statement(act_stmt: parser.NonterminalNode) -> Iterable[Statement]:
    assert act_stmt.prod_id == 'ActualStatement'
    stmt = cast_ntn(act_stmt.children[0])
    match stmt.prod_id:
        case 'Assignment':  # IDENTIFIER EQUALS Expr
            yield AssignmentStatement(
                line_number=None,
                identifier=cast_tn(stmt.children[0]).token.value,
                expr=cast_ntn(stmt.children[2])
            )
        case 'GotoStatement':  # GOTO LineNumber
            target_line_node = cast_ntn(stmt.children[1])
            target_line_terminal_node = cast_tn(target_line_node.children[0])
            target_line = int(target_line_terminal_node.token.value)
            yield GotoStatement(line_number=None, target_line=target_line)
        case 'PrintStatement':  # PRINT Expr
            yield PrintStatement(line_number=None, expr=cast_ntn(stmt.children[1]))
        case 'IfStatement':  # IF Expr THEN Statement ElseClause?
            then_stmts = list(_extract_statements(cast_ntn(stmt.children[3])))
            else_clause = cast_ntn(stmt.children[4])
            if else_clause.prod_id != 'ElseClause':
                # Compiled statements layout, with statement numbers relative to current statement
                # (where T = len(then_stmts)):
                # 0:    IF (else skip T statements)
                # 1..T: THEN statements
                # T+1:  Subsequent statements
                yield IfStatement(
                    line_number=None,
                    condition=cast_ntn(stmt.children[1]),
                    relative_jump_if_falsy=len(then_stmts)
                )
                yield from then_stmts
            else:
                else_stmts = list(_extract_statements(cast_ntn(else_clause.children[1])))
                # Compiled statements layout, with statement numbers relative to current statement
                # (where T = len(then_stmts), E = len(else_stmts)):
                # 0:           IF (else skip T+1 statements)
                # 1..T:        THEN statements
                # T+1:         skip E statements
                # T+2..T+E+1:  Subsequent statements
                yield IfStatement(
                    line_number=None,
                    condition=cast_ntn(stmt.children[1]),
                    relative_jump_if_falsy=len(then_stmts) + 1
                )
                yield from then_stmts
                yield RelativeJumpStatement(line_number=None, relative_jump=len(else_stmts))
                yield from else_stmts

        case _:
            raise BasicError(f'Unknown statement type: {stmt.prod_id}')


def _extract_statements(ast: parser.NonterminalNode) -> Iterable[Statement]:
    while ast.children:
        stmt = cast_ntn(ast.children[0])
        assert stmt.prod_id == 'Statement'
        substatements = list(_node_to_statement(cast_ntn(stmt.children[1])))
        line_number_node = cast_ntn(stmt.children[0])
        if line_number_node.prod_id == 'LineNumber':
            line_number_terminal_node = cast_tn(line_number_node.children[0])
            substatements[0].line_number = int(line_number_terminal_node.token.value)
        yield from substatements
        ast = cast_ntn(ast.children[1])


class BasicInterpreter:

    def __init__(self, prog: str) -> None:
        lex = lexer.Lexer(LEXER_RULES)
        self.parser = parser.Parser(lex, GRAMMAR)
        ast = cast_ntn(self.parser.parse(prog))
        self.statements = list(_extract_statements(ast))
        self.line_number_to_stmt_index = self._extract_line_numbers_to_stmt_indices()
        self.variables = dict[str, Any]()
        self.cur_statement = 0

    def exec(self) -> Iterable[str]:
        self.cur_statement = 0
        while self.cur_statement < len(self.statements):
            try:
                stmt = self.statements[self.cur_statement]
                yield from stmt.exec(self)
            except BasicError as ex:
                ex.add_note(f'While processing statement number {self.cur_statement+1}')
                raise ex

    def exec_statement(self, stmt: parser.NonterminalNode) -> Iterable[str]:
        stmt = cast_ntn(stmt.children[1])
        assert stmt.prod_id == 'ActualStatement'
        stmt = cast_ntn(stmt.children[0])
        match stmt.prod_id:
            case 'Assignment':  # IDENTIFIER EQUALS Expr
                identifier = cast_tn(stmt.children[0]).token.value
                self.variables[identifier] = self.evaluate_expr(cast_ntn(stmt.children[2]))
            case 'GotoStatement':  # GOTO LineNumber
                line_number_node = cast_ntn(stmt.children[1])
                line_number_terminal_node = cast_tn(line_number_node.children[0])
                line_number = int(line_number_terminal_node.token.value)
                if line_number not in self.line_number_to_stmt_index:
                    raise BasicError(f'GOTO specified an invalid target line number {line_number}')
                self.cur_statement = self.line_number_to_stmt_index[line_number]
                self.cur_statement -= 1  # To counteract +1 at end of loop
            case 'PrintStatement':  # PRINT Expr
                yield f'{self.evaluate_expr(cast_ntn(stmt.children[1]))}\n'
            case 'IfStatement':  # IF Expr THEN Statement ElseClause?
                condition = self.evaluate_expr(cast_ntn(stmt.children[1]))
                else_clause = cast_ntn(stmt.children[4])
                if condition:
                    yield from self.exec_statement(cast_ntn(stmt.children[3]))
                    self.cur_statement -= 1  # To countact +1 inside the inner call
                elif else_clause.prod_id == 'ElseClause':
                    self.exec_statement(cast_ntn(else_clause.children[1]))
                    self.cur_statement -= 1  # To countact +1 inside the inner call
            case _:
                raise BasicError(f'Unknown statement type: {stmt.prod_id}')
        self.cur_statement += 1

    def evaluate_expr(self, expr: parser.Node) -> Any:
        if isinstance(expr, parser.TerminalNode):
            match expr.token.token_id:
                case 'INTEGER_CONST':
                    return int(expr.token.value)
                case 'FLOAT_CONST':
                    return float(expr.token.value)
                case 'STRING_LITERAL':
                    return expr.token.value[1:-1]
                case 'IDENTIFIER':
                    identifier = expr.token.value
                    if identifier not in self.variables:
                        raise BasicError(f'Undefined variable: {identifier}')
                    return self.variables[identifier]
                case _:
                    raise BasicError(f'Unexpected terminal node of type {expr.token.token_id} when parsing expression')

        node = cast_ntn(expr)
        match node.prod_id:
            case 'Expr' | 'Expr3' | 'Expr2' | 'Expr1':
                left_value = self.evaluate_expr(node.children[0])
                return self.evaluate_operator(left_value, cast_ntn(node.children[1]))
            case 'Expr0':
                if len(node.children) == 1:
                    return self.evaluate_expr(node.children[0])
                first_child = cast_tn(node.children[0])
                if first_child.token.token_id == 'LEFT_PAREN':
                    # LEFT_PAREN Expr RIGHT_PAREN
                    return self.evaluate_expr(node.children[1])
                elif first_child.token.token_id == 'PREC_2_OPERATOR':
                    # PREC_2_OPERATOR NUMBER
                    return self.evaluate_operator(0, node)
                elif first_child.token.token_id == 'IDENTIFIER':
                    # IDENTIFIER
                    return self.evaluate_expr(node.children[0])
                else:
                    raise RuntimeError('Bug in the grammar!')
            case 'Literal':
                return self.evaluate_expr(node.children[0])
            case _:
                raise RuntimeError(f'Bug in the grammar: Unexpected node {node.prod_id}')

    def evaluate_operator(self, left_value: Any, maybe_operator_node: parser.NonterminalNode) -> Any:
        if not maybe_operator_node.children:
            return left_value
        operator_node = cast_tn(maybe_operator_node.children[0])
        operator = operator_node.token.value
        operator_fn: Callable[[float, float], float] = OPERATOR_FUNCS[operator]
        right_value = self.evaluate_expr(maybe_operator_node.children[1])
        return operator_fn(left_value, right_value)


    def _extract_line_numbers_to_stmt_indices(self) -> dict[int, int]:
        """Returns a map from BASIC "Line Number" to the statement index to which it refers."""
        line_number_to_stmt_index = dict[int, int]()
        for idx, stmt in enumerate(self.statements):
            if stmt.line_number is not None:
                if stmt.line_number in line_number_to_stmt_index:
                    raise BasicError(
                        f'Error: Statements {line_number_to_stmt_index[stmt.line_number]} and {idx} both have '
                        f'the line number {stmt.line_number}'
                    )
                line_number_to_stmt_index[stmt.line_number] = idx

        return line_number_to_stmt_index


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input-program-file>")

    with open(sys.argv[1], 'r') as f:
        program = f.read()

    interp = BasicInterpreter(program)
    for output in interp.exec():
        print(output)
