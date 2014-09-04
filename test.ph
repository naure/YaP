#!./pash.py

# Regular python stuff
print "Python"
x = {i: {j: j*2 for j in range(i)} for i in range(4)}

# Line comment

!echo Bash
truc = !echo template_{x.keys()}_{len(x)} fin
for k, v in x:  # EOL comment
    x[k] = !echo $v  # EOL after shell
files = ! ls -l
f = ! ls {var} -l
y = !y {var}

multi = process(!
    echo "A B"
    echo (parentheses)
    echo ! ignore
)

some_python = 'full output: ' + ! shell command
some_integer = 2 + (i! echo 2) + 2
list_of_lines = l! ls
rows_then_fields = f! ls -l
fields_then_rows = r! ls -l
print(!date +%s)
! echo {some_python.upper()}
! echo $strict_env_variable {$soft_env}
! echo stuff_$env_in_template {$soft_env}
print($env_variable)
if $1 == "first argument": pass
$unset_env_variable is None
