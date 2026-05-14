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
