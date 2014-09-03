#!./pash.py

print "Python"
x = {i: {j: j*2 for j in range(i)} for i in range(4)}
!echo Bash
truc = !echo _${x.keys()}_${len(x)}_ fin
for k, v in x:
    x[k] = ![echo $v]
files = ! ls -l
f = ! ls $var -l
y = ![y ${Y}]
