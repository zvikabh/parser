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
