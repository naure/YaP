
Yap

# Design Goals

## Truly integrated

Mix Shell and Python expressions. Outputs can be used
directly as strings, or easily interpreted in various ways.

Lots of convenience for scripting: $1 for sys.argv[1], $env_var, listdir, ...
Command interpolation with { any(expression) }.

## Safe:

Hell is quotes. And spaces in filenames. Or space-separated lists. When missing arguments gives an empty string messing up your paths. And logic with nothing but strings. Avoid all of this.

In Yap, code is independent of input. Python's data structures and logic are
well-defined. Missing arguments like $1 or environment variables like $var will
raise an error as expected.

    print($1)  # Raises an exception if missing
    print($1 or 'Default')  # Or provide an alternative

## Powerful:

Solve each task with the best suited language. Python for logic and shell for system
interaction.

## Simple:

Single file, no-dependencies compiler. On-the-fly or pre-compiled to
pure Python.

## Clear:

Any Python programmer should be able to understand Yap. And he should be able to
write some after glancing sideways at the examples in this README.



# Syntax:

## Output

* Default: Capture stdout, print stderr
    some_python = 'full output: ' + ! shell command

    some_integer = 2 + i! echo 2
    return_code = c! false
    stdout, stderr, return_code = sec! false
    list_of_lines = l! ls
    rows_then_fields = f! ls -l
    fields_then_rows = r! ls -l
    json = j! ls -l
    print(!(date +%s))

    output = !input|(wc)
    output = se!input| wc

    ! echo { some_python.upper() }
    ! echo $env_variable
    print($env_variable)
    if $1 == "first argument": pass
    $unset_env_variable is None
