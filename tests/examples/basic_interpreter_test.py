import unittest

import parser
from examples import basic_interpreter


class BasicInterpreterValidProgramsTest(unittest.TestCase):

    def test_hello_world(self) -> None:
        program = 'PRINT "Hello, world!"'
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "Hello, world!\n")

    def test_back_and_forth_conversion(self) -> None:
        program = '''
            print val(str$(4.5))
            print chr$(asc("HELLO"))
        '''
        runner = basic_interpreter.BasicInterpreter(program)
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
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "Hello, world!\n"*5 + "That's all, folks!\nThe end\n")

    def test_calculation(self) -> None:
        program = '''
            IFFY% = 5.1
            ELSEY% = IFFY% * 2
            10 PRINT IFFY% * 2 + ELSEY% * 4
        '''
        # Note that IFFY% is an integer, so 5.1 is rounded to 5
        runner = basic_interpreter.BasicInterpreter(program)
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
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '''\
*
**
***
****
*****
''')

    def test_calc_primes(self) -> None:
        program = '''
            let n% = 2
            10 div% = 2
            20 if div% > sqr(n%) then goto 40 end if
            mult% = div%
            30 if mult% = n% then goto 50 end if
            if mult% > n% then
                div% = div% + 1
                goto 20
            else
                mult% = mult% + div%
                goto 30
            end if
            40 print n%
            50 n% = n% + 1
            if n% < 20 then goto 10 end if
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '''\
2
3
5
7
11
13
17
19
''')


class BasicInterpreterInvalidCodeTest(unittest.TestCase):

    def test_expected_number(self) -> None:
        program = 'PRINT ABS("one")'
        runner = basic_interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(basic_interpreter.BasicError, 'Argument to function ABS must be of type Number'):
            list(runner.exec())

    def test_expected_string(self) -> None:
        program = 'PRINT LEN(3000)'
        runner = basic_interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(basic_interpreter.BasicError, 'Argument to function LEN must be of type str'):
            list(runner.exec())

    def test_missing_end_if(self) -> None:
        program = 'IF 2 > 1 THEN GOTO 10'
        with self.assertRaisesRegex(
            parser.ParserError, r'The terminal \$ is not allowed to start a derivation of ElseClause\?'
        ):
            basic_interpreter.BasicInterpreter(program)

    def test_missing_line_number(self) -> None:
        program = 'IF 2 > 1 THEN GOTO 10 END IF'
        runner = basic_interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(basic_interpreter.BasicError, 'GOTO specified an invalid target line number 10'):
            list(runner.exec())

    def test_type_mismatch(self) -> None:
        program = 'LET S = "foo"'
        runner = basic_interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(
            basic_interpreter.BasicError, 'Type mistmatch: Received value \'foo\' of type str, expecting Number'
        ):
            list(runner.exec())



if __name__ == '__main__':
    unittest.main()
