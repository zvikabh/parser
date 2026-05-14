from __future__ import annotations

import lexer
import parser


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
    ELSE[ignore_case=true]         r'ELSE\b'
    ENDIF[ignore_case=true]        r'END\s+IF\b'
    FOR[ignore_case=true]          r'FOR\b'
    GOTO[ignore_case=true]         r'GOTO\b'
    IF[ignore_case=true]           r'IF\b'
    LET[ignore_case=true]          r'LET\b'
    NEXT[ignore_case=true]         r'NEXT\b'
    PRINT[ignore_case=true]        r'PRINT\b'
    STEP[ignore_case=true]         r'STEP\b'
    THEN[ignore_case=true]         r'THEN\b'
    TO[ignore_case=true]           r'TO\b'
    WEND[ignore_case=true]         r'WEND\b'
    WHILE[ignore_case=true]        r'WHILE\b'
    FUNC_1ARG[ignore_case=true,to_upper=true]    r'((ABS|ASC|ATN|COS|EXP|INT|LEN|LOG|SGN|SIN|SQR|TAN|VAL)\b)|((STR|CHR)\$)'
    VARNAME_STR[to_upper=true]     r'[A-Za-z][A-Za-z0-9_]*\$'
    # We neglect the distinction between integer and long integers, and treat them all as Python integers, which have
    # unlimited range.
    VARNAME_INT[to_upper=true]     r'[A-Za-z][A-Za-z0-9_]*[\%\&]'
    # We neglect the distinction between single and double precision floats, and treat them all as double-precision.
    VARNAME_FLOAT[to_upper=true]   r'[A-Za-z][A-Za-z0-9_]*[\!\#]?'
'''


GRAMMAR = '''
    ROOT             -> Statement ROOT?;
    Statement        -> LineNumber? ActualStatement;
    LineNumber       -> INTEGER_CONST;
    ActualStatement  -> Assignment
                      | ForStatement
                      | GotoStatement
                      | IfStatement
                      | PrintStatement
                      | WhileStatement;
    Assignment       -> LET? VarName EQUALS Expr;
    ForStatement     -> FOR VarName EQUALS Expr TO Expr StepClause? ROOT? NEXT;
    StepClause       -> STEP Expr;
    GotoStatement    -> GOTO LineNumber;
    IfStatement      -> IF Expr THEN ROOT ElseClause? ENDIF;
    ElseClause       -> ELSE ROOT;
    PrintStatement   -> PRINT Expr;
    WhileStatement   -> WHILE Expr ROOT? WEND;
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
                      | FUNC_1ARG LEFT_PAREN Expr RIGHT_PAREN
                      | VarName;
    Literal          -> FLOAT_CONST
                      | INTEGER_CONST
                      | STRING_LITERAL;
    VarName          -> VARNAME_STR
                      | VARNAME_INT
                      | VARNAME_FLOAT;
'''


def get_basic_parser() -> parser.Parser:
    lex = lexer.Lexer(LEXER_RULES)
    return parser.Parser(lex, GRAMMAR)


def cast_ntn(node: parser.Node) -> parser.NonterminalNode:
    assert isinstance(node, parser.NonterminalNode)
    return node


def cast_tn(node: parser.Node) -> parser.TerminalNode:
    assert isinstance(node, parser.TerminalNode)
    return node
