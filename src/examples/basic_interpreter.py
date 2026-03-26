"""Interpreter for a simple version of the BASIC programming language."""
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
    IfStatement      -> IF Expr THEN Statement ElseClause? ENDIF;
    ElseClause       -> ELSE Statement;
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


def _extract_statements(ast: parser.NonterminalNode) -> Iterable[parser.NonterminalNode]:
    while ast.children:
        stmt = cast(parser.NonterminalNode, ast.children[0])
        assert stmt.prod_id == 'Statement'
        yield stmt
        ast = cast(parser.NonterminalNode, ast.children[1])


class BasicInterpreter:

    def __init__(self, prog: str) -> None:
        lex = lexer.Lexer(LEXER_RULES)
        self.parser = parser.Parser(lex, GRAMMAR)
        ast = cast(parser.NonterminalNode, self.parser.parse(prog))
        self.statements = list(_extract_statements(ast))
        self.line_number_to_stmt_index = self._extract_line_numbers_to_stmt_indices()
        self.variables = dict[str, Any]()
        self.cur_statement = 0

    def exec(self) -> Iterable[str]:
        self.cur_statement = 0
        while self.cur_statement < len(self.statements):
            try:
                stmt = self.statements[self.cur_statement]  # LineNumber? ActualStatement
                yield from self.exec_statement(stmt)
            except BasicError as ex:
                ex.add_note(f'While processing statement number {self.cur_statement+1}')
                raise ex

    def exec_statement(self, stmt: parser.NonterminalNode) -> Iterable[str]:
        stmt = cast(parser.NonterminalNode, stmt.children[1])
        assert stmt.prod_id == 'ActualStatement'
        stmt = cast(parser.NonterminalNode, stmt.children[0])
        match stmt.prod_id:
            case 'Assignment':  # IDENTIFIER EQUALS Expr
                identifier = cast(parser.TerminalNode, stmt.children[0]).token.value
                self.variables[identifier] = self.evaluate_expr(cast(parser.NonterminalNode, stmt.children[2]))
            case 'GotoStatement':  # GOTO LineNumber
                line_number_node = cast(parser.NonterminalNode, stmt.children[1])
                line_number_terminal_node = cast(parser.TerminalNode, line_number_node.children[0])
                line_number = int(line_number_terminal_node.token.value)
                if line_number not in self.line_number_to_stmt_index:
                    raise BasicError(f'GOTO specified an invalid target line number {line_number}')
                self.cur_statement = self.line_number_to_stmt_index[line_number]
                self.cur_statement -= 1  # To counteract +1 at end of loop
            case 'PrintStatement':  # PRINT Expr
                yield f'{self.evaluate_expr(cast(parser.NonterminalNode, stmt.children[1]))}\n'
            case 'IfStatement':  # IF Expr THEN Statement ElseClause?
                condition = self.evaluate_expr(cast(parser.NonterminalNode, stmt.children[1]))
                else_clause = cast(parser.NonterminalNode, stmt.children[4])
                if condition:
                    yield from self.exec_statement(cast(parser.NonterminalNode, stmt.children[3]))
                    self.cur_statement -= 1  # To countact +1 inside the inner call
                elif else_clause.prod_id == 'ElseClause':
                    self.exec_statement(cast(parser.NonterminalNode, else_clause.children[1]))
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

        node = cast(parser.NonterminalNode, expr)
        match node.prod_id:
            case 'Expr' | 'Expr3' | 'Expr2' | 'Expr1':
                left_value = self.evaluate_expr(node.children[0])
                return self.evaluate_operator(left_value, cast(parser.NonterminalNode, node.children[1]))
            case 'Expr0':
                if len(node.children) == 1:
                    return self.evaluate_expr(node.children[0])
                first_child = cast(parser.TerminalNode, node.children[0])
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
        operator_node = cast(parser.TerminalNode, maybe_operator_node.children[0])
        operator = operator_node.token.value
        operator_fn: Callable[[float, float], float] = OPERATOR_FUNCS[operator]
        right_value = self.evaluate_expr(maybe_operator_node.children[1])
        return operator_fn(left_value, right_value)


    def _extract_line_numbers_to_stmt_indices(self) -> dict[int, int]:
        """Returns a map from BASIC "Line Number" to the statement index to which it refers."""
        line_number_to_stmt_index = dict[int, int]()
        for idx, stmt in enumerate(self.statements):
            assert stmt.prod_id == 'Statement'
            first_child = cast(parser.NonterminalNode, stmt.children[0])
            if first_child.prod_id == 'LineNumber':
                line_number_terminal_node = cast(parser.TerminalNode, first_child.children[0])
                line_number = int(line_number_terminal_node.token.value)
                if line_number in line_number_to_stmt_index:
                    raise BasicError(
                        f'Error: Statements {line_number_to_stmt_index[line_number]} and {idx} both have '
                        f'the line number {line_number}'
                    )
                line_number_to_stmt_index[line_number] = idx

        return line_number_to_stmt_index


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input-program-file>")

    with open(sys.argv[1], 'r') as f:
        program = f.read()

    interp = BasicInterpreter(program)
    for output in interp.exec():
        print(output)
