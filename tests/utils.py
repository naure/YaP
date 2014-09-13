import difflib


def red(s):
    return '\033[91m' + s + '\033[0m'
def green(s):
    return '\033[92m' + s + '\033[0m'


def color_diffline(line):
    if line.startswith('-'):  # Red
        return red(line)
    if line.startswith('+'):  # Green
        return green(line)
    return line


def diff(a, b, **kwargs):
    return '\n'.join(map(
        color_diffline,
        difflib.unified_diff(
            a.splitlines(), b.splitlines(), **kwargs
        )))


def diff_paths(pa, pb):
    with open(pa) as fa, open(pb) as fb:
        a = fa.read()
        b = fb.read()

    if a != b:
        return diff(a, b, fromfile=pa, tofile=pb)
    else:
        return False


def compare_paths(ref_path, test_path, what='Output'):
    test_diff = diff_paths(ref_path, test_path)
    if test_diff:
        print(red('{} {} is different than reference {}'.format(
            what, test_path, ref_path)))
        print(test_diff)
        return 1
    else:
        return 0
