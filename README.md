
# YaP

A modern shell language derived from Python.

# Install

    sudo wget https://raw.githubusercontent.com/naure/YaP/master/yap.py -O /usr/local/bin/yap
    sudo chmod +x /usr/local/bin/yap

Then try:

    echo 'print( ! ls )' > list.yap
    yap list.yap

# Design Goals

## Truly integrated

Mix Shell and Python expressions, both ways. Outputs can be used
directly as strings, or easily interpreted in various ways.

Lots of straight-forward conveniences for arguments, files and strings handling.

Command interpolation with { any(expression) }.

## Safe:

Hell is quotes. And spaces in filenames. Or space-separated lists. When missing arguments gives an empty string messing up your paths. And logic with nothing but strings. Avoid all of this.

In Yap, code is independent of input. Python's data structures and logic are
well-defined. Missing arguments like $1 or environment variables like $var will
raise an error as expected.

    print($1)  # Raises an exception if missing
    print($1 or 'Default')  # Or provide an alternative

Failures of called processes must be handled, either implicitly or explicitely.

Besides, it does not contain prehistoric security bugs like bash :D

## Powerful:

Solve each task with the best suited language. Python for logic and shell for system
interaction. Cross-platform like Python.

## Simple:

Single file, no-dependencies compiler. On-the-fly or pre-compiled to
pure Python.

## Clear:

Any Python programmer should be able to understand Yap. And he should be able to
write some after glancing sideways at the examples in this README.


# Syntax:

## Running commands

    # Run command. Output will be printed on the console
    ! cmd

    # Capture output in an expression. stderr still goes to the console
    some_python = 'full output: ' + ! shell command
    print(! date +%s)

    # Specify what exactly to capture
    stdout, stderr = se! true
    output_and_errors = O! true

    # The above raise exceptions on failures. Instead, you can capture the return code
    return_code = c! true
    stdout, stderr, return_code = sec! false
    if return_code:
        error("Something went wrong")


## Variables in commands

    ! echo { some_python.upper() }
    ! touch prefix_{var}.ext

    # Safe program arguments. Exception if missing
    ! ls $1
    # Arguments list. Does not include the program name
    for arg in $*:
        ! ls {arg}

    # Same for environment variable
    ! echo $env_variable
    print($env_variable)

    # Test values or provide defaults
    ! ls { $1 or "." }
    if $1 == "first argument":
        pass
    $unknown_env_variable is None


## Working with files

    # Pipe to and from filenames with the > symbol
    (filename > ! wc > "words_count.txt")

    # Pipe from string
    (some_data ! cmd)

    # Read and write files
    some_data = read(filename)
    write(filename, some_data)

    # Many common operations are readily available
    exists(filename)
    joinpaths("/tmp", "dir", "file")
    listdir(".")
    glob("*.py")


## Working with data

    # Conversion of command outputs
    some_integer = (i! echo 2) + 2
    list_of_lines = l! ls
    rows_then_fields = f! ls -l
    fields_then_rows = r! ls -l
    json = j! ls -l

    # Join lists of strings
    concat, joinlines, joinfields

    # Filter text, list of lines, or an open file, with a regex
    for matching_line in grep("^pattern", open(file)):
        print(matching_line)

    # Pretty print and colors. Colors are simply ignored if not using a terminal.
    pprint(..), red(..), blue(..), green(..), ..


# Examples

## grep

yap grep.yp pattern files...

    for file in $*[1:]:
        print(green(file) + ':')
        print(concat(
            grep($1, open(file))
        ))

## Nice listing with file type

yap listing.yp [directory]

    print(gray('Listing nicely'))
    filenames = listdir($1 or '.')
    for name in filenames:
        print(
            blue(name.rjust(15)),
            joinfields(
                (f! file {name} )[1:]
            )
        )
