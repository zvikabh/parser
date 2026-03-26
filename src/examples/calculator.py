"""Computes arithmetic expressions with parentheses and operator precedence."""

import math
from typing import cast, Callable

import lexer
import parser


LEXER_RULES = r'''
    WHITESPACE[emit=false]         r'\s+'
    NUMBER                         r'([0-9]+(\.[0-9]*)?)|(\.[0-9]+)'
    PREC_0_OPERATOR                r'\*\*'
    PREC_1_OPERATOR                r'\*|\/'
    PREC_2_OPERATOR                r'\-|\+'
    LEFT_PAREN                     r'\('
    RIGHT_PAREN                    r'\)'
    FUNCTION_NAME[to_upper=true]   r'[A-Za-z][A-Za-z0-9]*'
'''


GRAMMAR = r'''
    ROOT      -> Expr;
    Expr      -> Expr2 MoreExpr?;
    MoreExpr  -> PREC_2_OPERATOR Expr;
    Expr2     -> Expr1 MoreExpr2?;
    MoreExpr2 -> PREC_1_OPERATOR Expr2;
    Expr1     -> Expr0 MoreExpr1?;
    MoreExpr1 -> PREC_0_OPERATOR Expr1;
    Expr0     -> NUMBER
               | PREC_2_OPERATOR NUMBER 
               | LEFT_PAREN Expr RIGHT_PAREN 
               | FUNCTION_NAME LEFT_PAREN Expr RIGHT_PAREN;
'''


OPERATOR_FUNCS = {
    '**': lambda x, y: x**y,
    '*': lambda x, y: x*y,
    '/': lambda x, y: x/y,
    '+': lambda x, y: x+y,
    '-': lambda x, y: x-y,
}


FUNCTION_FUNCS = {
    'SQRT': lambda x: math.sqrt(x),
    'ABS': lambda x: math.fabs(x),
}


def compute_node_value(node: parser.Node) -> float:
    if isinstance(node, parser.TerminalNode):
        if node.token.token_id == 'NUMBER':
            return float(node.token.value)
        raise parser.ParserError(f'Bug in grammar: reached terminal {node.token.token_id}')

    node = cast(parser.NonterminalNode, node)
    match node.prod_id:
        case 'ROOT':
            return compute_node_value(node.children[0])
        case 'Expr' | 'Expr2' | 'Expr1':
            left_value = compute_node_value(node.children[0])
            return compute_operator(left_value, cast(parser.NonterminalNode, node.children[1]))
        case 'Expr0':
            if len(node.children) == 1:
                return compute_node_value(node.children[0])
            first_child = cast(parser.TerminalNode, node.children[0])
            if first_child.token.token_id == 'LEFT_PAREN':
                # LEFT_PAREN Expr RIGHT_PAREN
                return compute_node_value(node.children[1])
            elif first_child.token.token_id == 'PREC_2_OPERATOR':
                # PREC_2_OPERATOR NUMBER
                return compute_operator(0, node)
            elif first_child.token.token_id == 'FUNCTION_NAME':
                # FUNCTION_NAME LEFT_PAREN Expr RIGHT_PAREN
                function_name = first_child.token.value
                function_fn = FUNCTION_FUNCS.get(function_name)
                if not function_fn:
                    raise parser.ParserError(f'Unknown function: {function_name}')
                return function_fn(compute_node_value(node.children[2]))
            else:
                raise RuntimeError('Bug in the grammar!')
        case _:
            raise RuntimeError(f'Bug in the grammar: Unexpected node {node.prod_id}')


def compute_operator(left_value: float, maybe_operator_node: parser.NonterminalNode) -> float:
    if not maybe_operator_node.children:
        return left_value
    operator_node = cast(parser.TerminalNode, maybe_operator_node.children[0])
    operator = operator_node.token.value
    operator_fn: Callable[[float, float], float] = OPERATOR_FUNCS[operator]
    right_value = compute_node_value(maybe_operator_node.children[1])
    return operator_fn(left_value, right_value)


class Calculator:

    def __init__(self) -> None:
        lex = lexer.Lexer(LEXER_RULES)
        self.parser = parser.Parser(lex, GRAMMAR)

    def calc(self, inp: str) -> float:
        return compute_node_value(self.parser.parse(inp))


if __name__ == '__main__':
    calc = Calculator()
    while True:
        inp = input('Enter arithmetic expression to calculate, or empty line to quit:\n> ')
        if not inp.strip():
            break
        print(calc.calc(inp))
