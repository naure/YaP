from subprocess import Popen, PIPE, STDOUT, CalledProcessError
import re

re_escape_sh = re.compile(r'([\\ ])')

def escape_sh(s):
    return re_escape_sh.sub(r'\\\1', s)

def yap_call(cmd, flags='', indata=None, convert=None):
    if 'h' in flags:  # Shell mode
        cmd = ' '.join(map(escape_sh, cmd))
    proc = Popen(
        cmd,
        stdin=PIPE if indata is not None else None,
        stdout=PIPE if ('o' in flags or 's' in flags) else None,
        stderr=(
            PIPE if 'e' in flags else
            STDOUT if 's' in flags else None),
        universal_newlines='b' not in flags,
        shell='h' in flags,
        env={} if 'v' in flags else None,
        bufsize=-1,  # Buffered
    )
    if 'p' in flags:  # Run in the background
        return proc
    out, err = proc.communicate(indata)
    code = proc.returncode
    ret = []
    if ('o' in flags or 's' in flags):
        if convert:
            ret.append(convert(out))
        else:
            ret.append(out)
    if 'e' in flags:
        ret.append(err)
    if 'r' in flags:
        ret.append(code)
    else:  # The user won't check the return code, so do it now
        if code != 0 and 'n' not in flags:
            raise CalledProcessError(code, cmd, ret)
    # Return either the unique output, the list of outputs, or None
    return ret[0] if len(ret) == 1 else ret or None
