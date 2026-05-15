from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

from examples.basic import compiler


class BasicCompilerTest(unittest.TestCase):

    def assert_program_lines_equal(self, prog1: str, prog2: str) -> None:
        prog1_strip = [line.strip() for line in prog1.split('\n') if line.strip()]
        prog2_strip = [line.strip() for line in prog2.split('\n') if line.strip()]
        self.assertEqual(prog2_strip, prog1_strip)

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

    def test_empty_while(self) -> None:
        prog = '''
            a% = 0
            while a% < 10
            wend
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            int main() {
                long var_A_int = 0;
                while ((((var_A_int)<(10)) ? -1 : 0)) {
                }
            }
        ''')

    def test_while(self) -> None:
        prog = '''
            a% = 0
            while a% < 10
                print a%
                a% = a% + 1
            wend
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            int main() {
                long var_A_int = 0;
                while ((((var_A_int)<(10)) ? -1 : 0)) {
                    std::cout << (var_A_int) << std::endl;
                    var_A_int = ((var_A_int)+(1));
                }
            }
        ''')

    def test_if(self) -> None:
        prog = '''
            A% = 0
            B! = 1
            IF A% < B! THEN PRINT "A" ELSE PRINT "B" END IF
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            #include <string>
            int main() {
                long var_A_int = 0;
                double var_B_float = 1;
                if ((((var_A_int)<(var_B_float)) ? -1 : 0)) {
                    std::cout << (std::string("A")) << std::endl;
                } else {
                    std::cout << (std::string("B")) << std::endl;
                }
            }
        ''')

    def test_for_simple(self) -> None:
        prog = '''
            FOR A% = 0 TO 10
                PRINT A%
            NEXT
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            int main() {
                long var_A_int = 0;
                for (; var_A_int <= (10); var_A_int += 1) {
                    std::cout << (var_A_int) << std::endl;
                }
            }
        ''')

    def test_for_with_step(self) -> None:
        prog = '''
            S% = 1 + 1
            FOR A% = 0 TO 10 STEP S%
                PRINT A%
            NEXT
        '''
        c_prog = compiler.BasicCompiler(prog).compile()
        self.assert_program_lines_equal(c_prog, '''
            #include <iostream>
            int main() {
                long var_S_int = ((1)+(1));
                long var_A_int = 0;
                for (; var_A_int <= (10); var_A_int += (var_S_int)) {
                    std::cout << (var_A_int) << std::endl;
                }
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

    def test_while_type_mistmatch(self) -> None:
        prog = '''
            A$ = "foo"
            while A$
            wend
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'WHILE condition must be a numeric type'):
            compiler.BasicCompiler(prog).compile()

    def test_while_unknown_var(self) -> None:
        prog = '''
            while A% < 10
            wend
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'Undefined variable: A%'):
            compiler.BasicCompiler(prog).compile()

    def test_if_type_mistmatch(self) -> None:
        prog = '''
            A$ = "foo"
            if A$ then print A$ end if
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'IF condition must be a numeric type'):
            compiler.BasicCompiler(prog).compile()

    def test_if_unknown_var(self) -> None:
        prog = 'if A% < 10 then print "foo" end if'
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'Undefined variable: A%'):
            compiler.BasicCompiler(prog).compile()

    def test_for_non_numeric_type(self) -> None:
        prog = '''
            FOR A$ = 0 TO 10
                PRINT A$
            NEXT
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError,
                                    r'FOR iteration variable A\$ must have a numeric type'):
            compiler.BasicCompiler(prog).compile()

    def test_for_initial_value_numeric_type(self) -> None:
        prog = '''
            FOR A% = "0" TO 10
                PRINT A%
            NEXT
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'FOR initial value must have a numeric type'):
            compiler.BasicCompiler(prog).compile()

    def test_for_stop_value_numeric_type(self) -> None:
        prog = '''
            FOR A% = 0 TO "5"
                PRINT A%
            NEXT
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'FOR stop value must have a numeric type'):
            compiler.BasicCompiler(prog).compile()

    def test_for_step_value_numeric_type(self) -> None:
        prog = '''
            B$ = "1"
            FOR A% = 0 TO 5 STEP B$
                PRINT A%
            NEXT
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'FOR step value must have a numeric type'):
            compiler.BasicCompiler(prog).compile()

    def test_for_step_value_undefined(self) -> None:
        prog = '''
            FOR A% = 0 TO 5 STEP B%
                PRINT A%
            NEXT
        '''
        with self.assertRaisesRegex(compiler.BasicCompilerError, r'Undefined variable: B%'):
            compiler.BasicCompiler(prog).compile()


# class BasicInterpreterIntegrationTests(unittest.TestCase):
#
#     def test_integration(self) -> None:
#         program_files = sorted(Path(f) for f in (Path(__file__).parent / 'integration').glob('*.bas'))
#         self.assertGreater(len(program_files), 0, 'No integration tests found')
#         expected_output_files = [fname.with_suffix('.expected_output.txt') for fname in program_files]
#
#         for program_file, expected_output_file in zip(program_files, expected_output_files):
#             with self.subTest(file=program_file):
#                 program = program_file.read_text()
#                 c_code = compiler.BasicCompiler(program).compile()
#                 with tempfile.TemporaryDirectory() as tmp:
#                     temp_dir = Path(tmp)
#                     c_filename = temp_dir / 'program.cc'
#                     c_filename.write_text(c_code)
#                     binary_filename = c_filename.with_suffix('.out')
#
#                     if platform.system() == 'Windows':
#                         result = subprocess.run(
#                             ['wsl', 'wslpath', '-a', str(c_filename).replace('\\', '\\\\')],
#                             # check=True,
#                             text=True,
#                             shell=True,
#                             capture_output=True
#                         )
#                         if result.returncode != 0:
#                             raise RuntimeError(f'wslpath failed with: {result.stderr} on fname {str(c_filename)}')
#                         c_filename_wsl = result.stdout.strip()
#                         binary_filename_wsl = c_filename_wsl + '.out'
#                         subprocess.run(
#                             ['wsl', 'bash', '-c', f'g++ {c_filename_wsl} -o {binary_filename_wsl}'],
#                             shell=True,
#                             check=True
#                         )
#                         output = subprocess.run(
#                             ['wsl', 'bash', '-c', str(binary_filename_wsl)], shell=True, check=True, capture_output=True
#                         ).stdout.decode()
#                     else:
#                         subprocess.run(['g++', c_filename, '-o', binary_filename], check=True)
#                         output = subprocess.run(binary_filename, check=True, text=True, capture_output=True).stdout
#
#                 self.assertEqual(output, expected_output_file.read_text())


if __name__ == '__main__':
    unittest.main()
