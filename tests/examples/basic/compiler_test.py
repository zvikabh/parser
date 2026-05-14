import unittest

import parser
from examples.basic import compiler


class BasicCompilerTest(unittest.TestCase):

    def assert_program_lines_equal(self, prog1: str, prog2: str) -> None:
        prog1_strip = [line.strip() for line in prog1.split('\n') if line.strip()]
        prog2_strip = [line.strip() for line in prog2.split('\n') if line.strip()]
        self.assertEqual(prog1_strip, prog2_strip)

    def test_goto(self) -> None:
        basic_prog = '''
            10 GOTO 20
            20 GOTO 10
        '''
        c_prog = compiler.BasicCompiler(basic_prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            int main() {
                line_10: goto line_20;
                line_20: goto line_10;
            }
        ''')

    def test_print_int(self) -> None:
        prog = 'PRINT 1'
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            int main() {
                std::cout << (1) << std::endl;
            }
        ''')

    def test_print_sum(self) -> None:
        prog = 'PRINT 1+1'
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            int main() {
                std::cout << (((1)+(1))) << std::endl;
            }
        ''')

    def test_print_precedence(self) -> None:
        prog = 'PRINT 1+2*3.0'
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            int main() {
                std::cout << (((1)+(((2)*(3.0))))) << std::endl;
            }
        ''')

    def test_print_funcs(self) -> None:
        prog = '''
            print abs(-1)
            print chr$(65)
            print sgn(5)
            print len("hello")
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <cmath>
            #include <iostream>
            #include <string>
            int main() {
                std::cout << (std::abs(((0)-(1)))) << std::endl;
                std::cout << (std::string(1, (char)(65))) << std::endl;
                std::cout << ((((5)<0)?-1:1)) << std::endl;
                std::cout << ((std::string("hello").size())) << std::endl;
            }
        ''')

    def test_infinite_loop(self) -> None:
        prog = '''
            10 print "Hello"
            goto 10
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            #include <string>
            int main() {
                line_10: std::cout << (std::string("Hello")) << std::endl;
                goto line_10;
            }
        ''')

    def test_assign_var(self) -> None:
        prog = '''
            let a$ = "hello"
            print A$
            a$ = "goodbye"
            print A$
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            #include <string>
            int main() {
                std::string var_A_str = std::string("hello");
                std::cout << (var_A_str) << std::endl;
                var_A_str = std::string("goodbye");
                std::cout << (var_A_str) << std::endl;
            }
        ''')

    def test_upcast_assignment(self) -> None:
        prog = '''
            let a% = 3
            b! = a%
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            int main() {
                long var_A_int = 3;
                double var_B_float = var_A_int;
            }
        ''')


class BasicCompilerErrorsTest(unittest.TestCase):

    def test_duplicate_line_numbers(self) -> None:
        prog = '''
            10 print 1
            10 print "Hello"
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, 'Duplicate line number: 10'):
            compiler.BasicCompiler(prog).compile()

    def test_undefined_variable(self) -> None:
        prog = 'print a$'
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'Undefined variable: A\$'):
            compiler.BasicCompiler(prog).compile()

    def test_operator_type_mismatch(self) -> None:
        prog = 'print 3+"a"'
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'Type mismatch in operator `\+`'):
            compiler.BasicCompiler(prog).compile()

    def test_func_type_mismatch_string_to_float(self) -> None:
        prog = 'print sin("foo")'
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'Type mismatch in SIN: Expected FLOAT, got STRING'):
            compiler.BasicCompiler(prog).compile()

    def test_func_type_mismatch_float_to_int(self) -> None:
        prog = 'print chr$(65.0)'
        with self.assertRaisesRegex(compiler.BasicCompilerError,
                                    r'Type mismatch in CHR\$: Expected INTEGER, got FLOAT'):
            compiler.BasicCompiler(prog).compile()

    def test_assignment_type_mismatch(self) -> None:
        prog = 'let a$ = 1'
        with self.assertRaisesRegex(compiler.BasicCompilerError,
                                    r'Variable A\$ cannot be assigned a value of type INTEGER'):
            compiler.BasicCompiler(prog).compile()


if __name__ == '__main__':
    unittest.main()
