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
