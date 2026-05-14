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
