#!./pash.py

# Regular python
print("Python")
numbers = {1: 'one', 2: 'two'}
print(sys.argv)

# Regular shell commands
!echo "Shell"
# Capture the output
now = ! date +%s
# Command in brackets. Print result
print(! date +%s)

multiline = (!
    echo A B
    -o (parentheses)
    -and ! are ignored
)

# Interpolation of commands
for key, value in numbers.items():
    !echo {key}={value}

!echo {"Any python expression, ignore in quotes".upper()}

# Environment variable in shell. Raises an error if missing.
! echo $HOME/somewhere
# Environment variable in Python. Returns None if missing.
$missing_variable is None
! echo a_{$variable or "default value"} b_c
! echo find . -exec cat {} +

# Same applies to program arguments
if $1:
    !echo "First argument: $1"
    for arg in $*:
        print(arg)


# Output conversion
file_list = l! ls -1

simple_string = 'Output: ' + ! echo some output
from_json = j! echo "[1, 2]"
to_integer = 2 + (i! echo 2) + 2
list_of_lines = l! ls
rows_then_columns = c! ls -l
fields_then_rows = r! ls -l
binary = b! echo cat doc.pdf

# Print stdout and stderr
! echo
# Capture stdout, print stderr
out = ! echo
# Capture stderr, print stdout
err = e! echo
# Capture both
out, err = oe! echo
# Include the return code
out, err, ret = oer! echo "Ok!"
if ret == 0:
    print(out)
# n to ignore errors
n! false unsafe cmd
# p to run in the background and get a proc object
proc = p! echo sleep 1
ret = proc.wait()
# h to run through a shell
print(h! echo a b | grep a)
