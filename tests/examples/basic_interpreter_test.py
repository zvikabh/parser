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

    def test_calc_primes_with_basic_stmts_only(self) -> None:
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

    def test_while(self) -> None:
        program = '''
            N% = 0
            WHILE N% < 10
                PRINT N%
                N% = N% + 1
            WEND
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '\n'.join(str(n) for n in range(10)) + '\n')

    def test_nested_while(self) -> None:
        program = '''
            N% = 1
            WHILE N% <= 5
                J% = 0
                S$ = ""
                WHILE J% < 5 - N%
                    S$ = S$ + " "
                    J% = J% + 1
                WEND
                J% = 0
                WHILE J% < N%
                    S$ = S$ + "**"
                    J% = J% + 1
                WEND
                PRINT S$
                N% = N% + 1
            WEND
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '''\
    **
   ****
  ******
 ********
**********
''')

    def test_calc_primes_with_while(self) -> None:
        program = '''
            LET N% = 1
            10 WHILE N% < 20
                N% = N% + 1
                DIV% = 2
                WHILE DIV% <= SQR(N%)
                    MULT% = DIV%
                    WHILE MULT% < N%
                        MULT% = MULT% + DIV%
                        IF MULT% = N% THEN
                            GOTO 10
                        END IF
                    WEND
                    DIV% = DIV% + 1
                WEND
                PRINT N%
            WEND
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

    def test_for_loop(self) -> None:
        program = '''
            for i% = 1 to 5
                print i%
            next
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '1\n2\n3\n4\n5\n')

    def test_for_loop_with_step(self) -> None:
        program = '''
            for i% = 2 to 10 step 2
                print i%
            next
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, '2\n4\n6\n8\n10\n')

    def test_calc_primes_with_for(self) -> None:
        program = '''
            n% = 2
            while n% < 20
                for div% = 2 to sqr(n%)
                    for mult% = div% to n% step div%
                        if mult% = n% then
                            goto 10 
                        end if
                    next
                next
                print n%
                10 n% = n% + 1
            wend
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

    def test_type_mismatch_in_func(self) -> None:
        program = 'PRINT ASC(5)'
        runner = basic_interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(
            basic_interpreter.BasicError,
            'Argument to function ASC must be of type str, but received value 5 of type int'
        ):
            list(runner.exec())

    def test_type_mismatch_in_operator(self) -> None:
        program = 'PRINT "A" * 4'
        runner = basic_interpreter.BasicInterpreter(program)
        with self.assertRaisesRegex(
            basic_interpreter.BasicError,
            'Type mistmatch in call to operator `\\*`: Left argument \'A\' has type str'
        ):
            list(runner.exec())



if __name__ == '__main__':
    unittest.main()
