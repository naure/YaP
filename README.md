
# YaP

A modern shell language derived from Python.

# Install

    sudo wget https://raw.githubusercontent.com/naure/YaP/master/yap.py -O /usr/local/bin/yap
    sudo chmod +x /usr/local/bin/yap

Then try:

    echo 'print( ! ls )' > list_example.yap
    yap list_example.yap

# Design Goals

## Truly integrated

The best of both worlds: Python code and inline shell commands. Outputs can be interpreted
directly as strings, lists of lines, csv, or json objects.

Lots of straight-forward conveniences for arguments, files, strings and errors handling.

Command interpolation with { any(expression) }.

## Safe:

Shell scripting is tricky, error-prone and unsafe. 
Hell is quotes. And spaces in filenames. Or space-separated lists. When missing arguments gives an empty string messing up your paths. And logic with nothing but strings. Avoid all of this.

Yap is a normal programming language; the code doesn't depend on input values. It uses the well-defined Python's data structures and logic. Common cases like missing arguments will raise an error as expected.

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
    stdout, stderr = oe! true
    output_and_errors = O! true

    # The above raise exceptions on failures. Instead, you can capture the return code
    return_code = r! true
    stdout, stderr, return_code = oer! false
    if return_code:
        error("Something went wrong")

    # The s prefix runs the command in a shell
    s! cat foo | grep bar


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
    some_float = (d! echo 2.5) + 2
    list_of_lines = l! ls
    list_of_words = f! ls
    lines_then_fields = lf! ls -l
    fields_then_lines = fl! ls -l
    json = j! ls -l

    # Join lists of strings
    concat, joinlines, joinfields

    # Filter text, list of lines, or an open file, with a regex
    for matching_line in grep("^pattern", open(file)):
        print(matching_line)

    # Pretty print and colors. Colors are simply ignored if not using a terminal.
    pprint(..), red(..), blue(..), green(..), ..


# Examples

## Nice colored listing with file type

yap listing.yp [directory]

    #!/usr/bin/env yap

    print(gray('Listing nicely'))
    filenames = listdir($1 or '.')
    for name in filenames:
        print(
            blue(name.rjust(15)),
            joinfields(
                (f! file {name} )[1:]
            )
        )

## Simple grep clone

yap grep.yp pattern files...

    #!/usr/bin/env yap
    
    for file in $*[1:]:
        print(green(file) + ':')
        print(concat(
            grep($1, open(file))
        ))

# Status

We use and maintain YaP at deckard.ai.
