#!/usr/bin/env python3
import sys
from collections import defaultdict, namedtuple
import yaml

Func = namedtuple('Func', ['calls'])
Call = namedtuple('Call', ['args', 'returns'])

def newFunc():
    return Func([])

def format_db(db):
    return yaml.dump(db)

def format_db_(db):
    return '\n\n'.join(
        '{}\n{}'.format(
            fid,
            format_func(func)
        )
        for fid, func in db.items()
    )

def format_func(func):
    return '\n'.join(map(format_call, func.calls))

def format_call(call):
    return '{} -> {}'.format(call.args, call.returns)

def fnid(frame):
    return '{}:{}'.format(
        frame.f_code.co_filename,
        frame.f_code.co_name,
    )

def serialize(o):
    try:
        return yaml.dump(o)
    except TypeError:
        return '<object>'


def trace(fn, fn_args=[]):
    fndb = defaultdict(newFunc)
    call_stack = []

    def trace_body(frame, event, value):
        func_id = fnid(frame)

        if event == 'return':
            call_args = call_stack.pop()
            func = fndb[func_id]
            func.calls.append(Call(
                serialize(call_args),
                serialize(value),
            ))
        return trace_body

    def trace_calls(frame, event, value):

        filename = frame.f_code.co_filename
        funcname = frame.f_code.co_name
        if(filename.startswith('/') or
            filename.startswith('<') or
            funcname.startswith('<')
           ):
            return  # Ignore built-in, library calls, generators, ..
            # XXX Not very reliable

        if event == 'call':
            call_args = dict(frame.f_locals)
            call_stack.append(call_args)
            return trace_body

    sys.settrace(trace_calls)
    fn(*fn_args)
    sys.settrace(None)
    return fndb


if __name__ == '__main__':
    z = 12

    def f(x):
        y = x + z
        return y

    def main():
        print(f(2))

    fndb = trace(main)
    print(format_db(fndb))
