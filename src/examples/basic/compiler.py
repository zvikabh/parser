"""Compiles a BASIC program into C++ code."""
from __future__ import annotations

import enum
import sys
from typing import Any, Callable

import parser
from examples.basic import grammar
from examples.basic.grammar import cast_ntn, cast_tn


class BasicCompilerError(Exception):
    """Error compiling the BASIC code."""


class BasicType(enum.Enum):
    STRING = 1
    INTEGER = 2
    FLOAT = 3

    def c_type(self) -> str:
        return {
            BasicType.STRING: 'std::string',
            BasicType.INTEGER: 'long',
            BasicType.FLOAT: 'double',
        }[self]

    @classmethod
    def castable(cls, from_type: BasicType, to_type: BasicType) -> bool:
        if from_type == to_type:
            return True
        if from_type == BasicType.INTEGER and to_type == BasicType.FLOAT:
            return True
        return False


def get_line_label(line_number: int) -> str:
    return f'line_{line_number}'


# Map from BASIC function name to tuple (input type, output type, #includes, translator)
_ONE_ARG_FUNCS: dict[str, tuple[BasicType, BasicType, list[str], Callable[[str], str]]] = {
    'ABS': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::abs({x})'),
    'ASC': (BasicType.STRING, BasicType.INTEGER, [], lambda x: f'int((x)[0])'),
    'ATN': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::atan({x})'),
    'CHR$': (BasicType.INTEGER, BasicType.STRING, ['string'], lambda x: f'std::string(1, (char)({x}))'),
    'COS': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::cos({x})'),
    'EXP': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::exp({x})'),
    'INT': (BasicType.FLOAT, BasicType.INTEGER, [], lambda x: f'int({x})'),
    'LEN': (BasicType.STRING, BasicType.INTEGER, [], lambda x: f'({x}.size())'),
    'LOG': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::log({x})'),
    'SGN': (BasicType.FLOAT, BasicType.FLOAT, [], lambda x: f'((({x})<0)?-1:1)'),
    'SIN': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::sin({x})'),
    'SQR': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::sqrt({x})'),
    'STR$': (BasicType.FLOAT, BasicType.STRING, ['string'], lambda x: f'std::to_string({x})'),
    'TAN': (BasicType.FLOAT, BasicType.FLOAT, ['cmath'], lambda x: f'std::tan({x})'),
    'VAL': (BasicType.STRING, BasicType.FLOAT, ['string'], lambda x: f'std::stof({x})'),
}


def get_op_translator(c_operator: str) -> Callable[[str, str], str]:
    """Returns an operator translator which uses the given C operator."""
    def translate_op(x: str, y: str) -> str:
        return f'(({x}){c_operator}({y}))'
    return translate_op


def get_boolean_op_translator(c_operator: str) -> Callable[[str, str], str]:
    """Returns an operator translator which translates `true` and `false` to -1 and 0, respectively."""
    def translate_op(x: str, y: str) -> str:
        return f'((({x}){c_operator}({y})) ? -1 : 0)'
    return translate_op


# Map from BASIC operator to tuple (list of possible input and output types, #includes, translator)
_OPERATORS: dict[str, tuple[list[tuple[BasicType, BasicType]], list[str], Callable[[str, str], str]]] = {
    '+': ([(BasicType.INTEGER, BasicType.INTEGER), (BasicType.FLOAT, BasicType.FLOAT)], [], get_op_translator('+')),
    '-': ([(BasicType.INTEGER, BasicType.INTEGER), (BasicType.FLOAT, BasicType.FLOAT)], [], get_op_translator('-')),
    '*': ([(BasicType.INTEGER, BasicType.INTEGER), (BasicType.FLOAT, BasicType.FLOAT)], [], get_op_translator('*')),
    # Division always returns a float in BASIC. Integer inputs are upcasted.
    '/': ([(BasicType.FLOAT, BasicType.FLOAT)], [], get_op_translator('/')),
    '**': ([(BasicType.FLOAT, BasicType.FLOAT)], ['cmath'], lambda x, y: f'std::pow({x}, {y})'),
    # We cast boolean operators to int so that printing them will show `0` or `1` rather than `true` or `false`.
    '=': ([(BasicType.FLOAT, BasicType.INTEGER), (BasicType.STRING, BasicType.INTEGER)], [],
          get_boolean_op_translator('==')),
    '>': ([(BasicType.FLOAT, BasicType.INTEGER), (BasicType.STRING, BasicType.INTEGER)], [],
          get_boolean_op_translator('>')),
    '<': ([(BasicType.FLOAT, BasicType.INTEGER), (BasicType.STRING, BasicType.INTEGER)], [],
          get_boolean_op_translator('<')),
    '<=': ([(BasicType.FLOAT, BasicType.INTEGER), (BasicType.STRING, BasicType.INTEGER)], [],
           get_boolean_op_translator('<=')),
    '>=': ([(BasicType.FLOAT, BasicType.INTEGER), (BasicType.STRING, BasicType.INTEGER)], [],
          get_boolean_op_translator('>=')),
}


class BasicCompiler:

    def __init__(self, prog: str) -> None:
        self.parser = grammar.get_basic_parser()
        self.ast = cast_ntn(self.parser.parse(prog))
        self.includes = set[str]()
        self.line_numbers = set[int]()
        self.variables = set[str]()

    def compile(self) -> str:
        c_stmts = ['int main() {'] + self._compile_statements(self.ast, indent=1) + ['}']
        includes_list = '\n'.join(f'#include <{inc_file}>' for inc_file in sorted(self.includes))
        return includes_list + '\n' + '\n'.join(c_stmts)

    def _compile_statements(self, stmts: parser.NonterminalNode, indent: int) -> list[str]:
        # Side effect: update self.variables, self.line_numbers, and self.includes
        c_stmts = list[str]()
        while stmts.children:
            basic_stmt = cast_ntn(stmts.children[0])
            assert basic_stmt.prod_id == 'Statement'
            c_stmts.append(self._basic_to_c_stmt(basic_stmt, indent))
            stmts = cast_ntn(stmts.children[1])
        return c_stmts

    def _basic_to_c_stmt(self, basic_stmt: parser.NonterminalNode, indent: int) -> str:
        c_stmt = '  ' * indent
        c_stmt += self._line_number_to_c_label(line_number_node=cast_ntn(basic_stmt.children[0]))
        actual_stmt = cast_ntn(basic_stmt.children[1])
        assert actual_stmt.prod_id == 'ActualStatement'
        inner_stmt = cast_ntn(actual_stmt.children[0])
        stmt_translator = self._PROD_ID_TO_STMT_TRANSLATOR[inner_stmt.prod_id]
        return c_stmt + stmt_translator(self, inner_stmt, indent)

    def _line_number_to_c_label(self, line_number_node: parser.NonterminalNode) -> str:
        if line_number_node.prod_id != 'LineNumber':
            return ''  # Statement does not have a line number

        line_number_terminal_node = cast_tn(line_number_node.children[0])
        line_number = int(line_number_terminal_node.token.value)
        if line_number in self.line_numbers:
            raise BasicCompilerError(f"Duplicate line number: {line_number}")
        self.line_numbers.add(line_number)
        return get_line_label(line_number) + ': '

    def _translate_goto_stmt(self, stmt: parser.NonterminalNode, indent: int) -> str:
        # GOTO LineNumber
        target_line_node = cast_ntn(stmt.children[1])
        target_line_terminal_node = cast_tn(target_line_node.children[0])
        target_line = int(target_line_terminal_node.token.value)
        return f'goto {get_line_label(target_line)};'

    def _translate_print_stmt(self, stmt: parser.NonterminalNode, indent: int) -> str:
        # PRINT Expr
        self.includes.add('iostream')
        expr = cast_ntn(stmt.children[1])
        assert expr.prod_id == 'Expr'
        c_expr, _ = self._translate_expr(expr)
        return f'std::cout << ({c_expr}) << std::endl;'

    def _translate_assignment_stmt(self, stmt: parser.NonterminalNode, indent: int) -> str:
        # LET? VarName EQUALS Expr
        var_name_ntn = cast_ntn(stmt.children[1])
        var_name_tn = cast_tn(var_name_ntn.children[0])
        basic_var_name = var_name_tn.token.value
        c_var_name, var_type = self._translate_varname(basic_var_name)
        c_new_value, new_value_type = self._translate_expr(stmt.children[3])
        if not BasicType.castable(from_type=new_value_type, to_type=var_type):
            raise BasicCompilerError(
                f'Type mismatch: Variable {basic_var_name} cannot be assigned a value of type {new_value_type.name}'
            )
        if basic_var_name in self.variables:
            # Re-assignment
            return f'{c_var_name} = {c_new_value};'
        else:
            # New variable
            self.variables.add(basic_var_name)
            if var_type == BasicType.STRING:
                self.includes.add('string')
            return f'{var_type.c_type()} {c_var_name} = {c_new_value};'

    def _translate_while_stmt(self, stmt: parser.NonterminalNode, indent: int) -> str:
        # WHILE Expr ROOT? WEND
        while_expr, while_type = self._translate_expr(stmt.children[1])
        if while_type != BasicType.INTEGER and while_type != BasicType.FLOAT:
            raise BasicCompilerError("WHILE condition must be a numeric type")
        loop_stmts = self._compile_statements(cast_ntn(stmt.children[2]), indent=indent + 1)
        c_code = [f'while ({while_expr}) {{'] + loop_stmts + ['  ' * indent + '}']
        return '\n'.join(c_code)

    _PROD_ID_TO_STMT_TRANSLATOR: dict[str, Callable[[BasicCompiler, parser.NonterminalNode, int], str]] = {
        'Assignment': _translate_assignment_stmt,
        'GotoStatement': _translate_goto_stmt,
        'PrintStatement': _translate_print_stmt,
        'WhileStatement': _translate_while_stmt,
    }

    def _translate_expr(self, expr: parser.Node) -> tuple[str, BasicType]:
        if isinstance(expr, parser.TerminalNode):
            match expr.token.token_id:
                case 'INTEGER_CONST':
                    return expr.token.value, BasicType.INTEGER
                case 'FLOAT_CONST':
                    return expr.token.value, BasicType.FLOAT
                case 'STRING_LITERAL':
                    self.includes.add('string')
                    s = expr.token.value.replace('\\', '\\\\')  # Escape backslashes to avoid special C chars
                    return f'std::string({s})', BasicType.STRING
                case 'VARNAME_STR' | 'VARNAME_INT' | 'VARNAME_FLOAT':
                    identifier = expr.token.value
                    if identifier not in self.variables:
                        raise BasicCompilerError(f'Undefined variable: {identifier}')
                    return self._translate_varname(identifier)
                case _:
                    raise BasicCompilerError(
                        f'Unexpected terminal node of type {expr.token.token_id} when parsing expression'
                    )

        node = cast_ntn(expr)
        match node.prod_id:
            case 'Expr' | 'Expr3' | 'Expr2' | 'Expr1':
                left_value, left_type = self._translate_expr(node.children[0])
                return self._translate_operator(left_value, left_type, cast_ntn(node.children[1]))
            case 'Expr0':
                if len(node.children) == 1:
                    return self._translate_expr(node.children[0])
                first_child = cast_tn(node.children[0])
                match first_child.token.token_id:
                    case 'LEFT_PAREN':  # LEFT_PAREN Expr RIGHT_PAREN
                        inner_expr, basic_type = self._translate_expr(node.children[1])
                        return '(' + inner_expr + ')', basic_type
                    case 'PREC_2_OPERATOR':  # PREC_2_OPERATOR NUMBER
                        return self._translate_operator('0', BasicType.INTEGER, node)
                    case 'VarName':
                        return self._translate_expr(first_child)
                    case 'FUNC_1ARG':  # FUNC_1ARG LEFT_PAREN Expr RIGHT_PAREN
                        func_name = cast_tn(node.children[0]).token.value
                        reqd_input_type, output_type, includes, fn = _ONE_ARG_FUNCS[func_name]
                        self.includes.update(includes)
                        arg, arg_type = self._translate_expr(node.children[2])
                        if not BasicType.castable(from_type=arg_type, to_type=reqd_input_type):
                            raise BasicCompilerError(
                                f'Type mismatch in {func_name}: Expected {reqd_input_type.name}, got {arg_type.name}'
                            )
                        return fn(arg), output_type
                    case _:
                        raise RuntimeError('Bug in the grammar!')
            case 'VarName' | 'Literal':
                return self._translate_expr(node.children[0])
            case _:
                raise RuntimeError(f'Bug in the grammar: Unexpected node {node.prod_id}')

    def _translate_operator(
        self, left_value: str, left_type: BasicType, maybe_operator_node: parser.NonterminalNode
    ) -> tuple[str, BasicType]:
        if not maybe_operator_node.children:
            return left_value, left_type
        operator_node = cast_tn(maybe_operator_node.children[0])
        operator = operator_node.token.value
        allowed_types, includes, translator = _OPERATORS[operator]
        right_value, right_type = self._translate_expr(maybe_operator_node.children[1])
        for allowed_input_type, output_type in allowed_types:
            if (BasicType.castable(from_type=left_type, to_type=allowed_input_type) and
                BasicType.castable(from_type=right_type, to_type=allowed_input_type)):
                self.includes.update(includes)
                return translator(left_value, right_value), output_type

        raise BasicCompilerError(
            f'Type mismatch in operator `{operator}`: Arguments have types {left_type.name} and {right_type.name}, '
            f'but operator `{operator}` requires both arguments to be of type '
            f'{[allow_type.name for allow_type, _ in allowed_types]}'
        )

    def _translate_varname(self, varname: str) -> tuple[str, BasicType]:
        if varname.endswith('$'):
            return f'var_{varname[:-1]}_str', BasicType.STRING
        if varname.endswith('%') or varname.endswith('&'):
            return f'var_{varname[:-1]}_int', BasicType.INTEGER
        if varname.endswith('!') or varname.endswith('#'):
            return f'var_{varname[:-1]}_float', BasicType.FLOAT
        return f'var_{varname[:-1]}_float', BasicType.FLOAT


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input-program-file>")

    with open(sys.argv[1], 'r') as f:
        program = f.read()

    compiler = BasicCompiler(program)
