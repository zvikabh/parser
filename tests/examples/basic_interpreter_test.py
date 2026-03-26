import unittest

from examples import basic_interpreter


class BasicInterpreterTest(unittest.TestCase):

    def test_hello_world(self) -> None:
        program = '''
            PRINT "Hello, world!"
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "Hello, world!\n")

    def test_hello_world_5_times(self) -> None:
        program = '''
            I = 0
            10 PRINT "Hello, world!"
            I = I + 1
            IF I < 5 THEN 
                GOTO 10
            END IF
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "Hello, world!\n"*5)

    def test_calculation(self) -> None:
        program = '''
            IFFY = 5
            ELSEY = IFFY * 2
            10 PRINT IFFY * 2 + ELSEY * 4
        '''
        runner = basic_interpreter.BasicInterpreter(program)
        output = ''.join(runner.exec())
        self.assertEqual(output, "50\n")


if __name__ == '__main__':
    unittest.main()
