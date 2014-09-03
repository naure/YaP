#!./pash.py

print "Python"
x = {i: {j: j*2 for j in range(i)} for i in range(4)}
!echo Bash
truc = !echo _{x.keys()}_{len(x)}_ fin
for k, v in x:
    x[k] = !(echo $v)
files = ! ls -l
f = ! ls {var} -l
y = !(y {var})

some_python = 'full output: ' + ! shell command
some_integer = 2 + i! echo 2
list_of_lines = l! ls
rows_then_fields = f! ls -l
fields_then_rows = r! ls -l
print(!(date +%s))
! echo {some_python.upper()}
! echo $env_variable {$long_env}
print($env_variable)
if $1 == "first argument": pass
$unset_env_variable is None
