from pathlib import Path
import unittest

import parser
from examples.basic import interpreter


class BasicInterpreterValidProgramsTest(unittest.TestCase):

    def test_hello_world(self) -> None:
        program = 'PRINT "Hello, world!"'
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "Hello, world!\n")

    def test_back_and_forth_conversion(self) -> None:
        program = '''
            print val(str$(4.5))
            print chr$(asc("HELLO"))
        '''
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "4.5\nH\n")

    def test_hello_world_5_times(self) -> None:
        program = '''
            I = 0
            10 PRINT "Hello, world!"
            I = I + 1
            IF I < 5 THEN 
                GOTO 10
            ELSE
                PRINT "That's all, folks!"
                PRINT "The end"
            END IF
        '''
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "Hello, world!\n"*5 + "That's all, folks!\nThe end\n")

    def test_calculation(self) -> None:
        program = '''
            IFFY% = 5.1
            ELSEY% = IFFY% * 2
            10 PRINT IFFY% * 2 + ELSEY% * 4
        '''
        # Note that IFFY% is an integer, so 5.1 is rounded to 5
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "50\n")

    def test_print_triangle(self) -> None:
        program = '''
            I = 1
            10 J = 0
            S$ = ""
            20 S$ = S$ + "*"
            J = J + 1
            IF J < I THEN
                GOTO 20
            END IF
            PRINT S$
            I = I + 1
            IF I <= 5 THEN
                GOTO 10
            END IF
        '''
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '''\
*
**
***
****
*****
''')

    def test_while(self) -> None:
        program = '''
            N% = 0
            WHILE N% < 10
                PRINT N%
                N% = N% + 1
            WEND
        '''
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '\n'.join(str(n) for n in range(10)) + '\n')

    def test_for_loop(self) -> None:
        program = '''
            for i% = 1 to 5
                print i%
            next
        '''
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '1\n2\n3\n4\n5\n')

    def test_for_loop_with_step(self) -> None:
        program = '''
            for i% = 2 to 10 step 2
                print i%
            next
        '''
        runner = interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '2\n4\n6\n8\n10\n')


class BasicInterpreterInvalidCodeTest(unittest.TestCase):

    def test_expected_number(self) -> None:
        program = 'PRINT ABS("one")'
        runner = interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(interpreter.BasicError, 'Argument to function ABS must be of type Number'):
            list(runner.exec())

    def test_expected_string(self) -> None:
        program = 'PRINT LEN(3000)'
        runner = interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(interpreter.BasicError, 'Argument to function LEN must be of type str'):
            list(runner.exec())

    def test_missing_end_if(self) -> None:
        program = 'IF 2 > 1 THEN GOTO 10'
        with self.assertRaisesRegex(
            parser.ParserError, r'The terminal \$ is not allowed to start a derivation of ElseClause\?'
        ):
            interpreter.BasicInterpreter(program)

    def test_missing_line_number(self) -> None:
        program = 'IF 2 > 1 THEN GOTO 10 END IF'
        runner = interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(interpreter.BasicError, 'GOTO specified an invalid target line number 10'):
            list(runner.exec())

    def test_type_mismatch(self) -> None:
        program = 'LET S = "foo"'
        runner = interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(
            interpreter.BasicError, 'Type mistmatch: Received value \'foo\' of type str, expecting Number'
        ):
            list(runner.exec())

    def test_type_mismatch_in_func(self) -> None:
        program = 'PRINT ASC(5)'
        runner = interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(
            interpreter.BasicError,
            'Argument to function ASC must be of type str, but received value 5 of type int'
        ):
            list(runner.exec())

    def test_type_mismatch_in_operator(self) -> None:
        program = 'PRINT "A" * 4'
        runner = interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(
            interpreter.BasicError,
            'Type mistmatch in call to operator `\\*`: Left argument \'A\' has type str'
        ):
            list(runner.exec())


class BasicInterpreterIntegrationTests(unittest.TestCase):

    def test_integration(self) -> None:
        program_files = sorted(Path(f) for f in (Path(__file__).parent / 'integration').glob('*.bas'))
        self.assertGreater(len(program_files), 0, 'No integration tests found')
        expected_output_files = [fname.with_suffix('.expected_output.txt') for fname in program_files]

        for program_file, expected_output_file in zip(program_files, expected_output_files):
            with self.subTest(file=program_file):
                program = program_file.read_text()
                runner = interpreter.BasicInterpreter(program)
                output = ''.join(runner.exec())
                self.assertEqual(output, expected_output_file.read_text())


if __name__ == '__main__':
    unittest.main()
