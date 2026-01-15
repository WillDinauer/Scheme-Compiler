import enum
from parser import scheme_parse

class SI:
    def __init__(self, mask, tag, shift):
        self.mask = mask
        self.tag = tag
        self.shift = shift

SHIFT_INFO = {
    "fixnum": SI(mask=(1<<2)-1, tag=0, shift=2),
    "char": SI(mask=(1<<9)-1, tag=(1<<5)-1, shift=8),
    "bool": SI(mask=(1<<8)-1, tag=(1<<6)-1, shift=7),
    "empty_list": SI(mask=(1<<9)-1, tag=47, shift=0)    # EL value is the tag...?
}

SYSTEM_TYPE = 64

def tag_ptr(value, type):
    si = SHIFT_INFO[type]
    if value >= 2 ** (SYSTEM_TYPE - si.shift):
        raise ValueError(f"{type} value {value} too large to store")
    
    # Shift and tag
    value = value << si.shift
    value |= si.tag

    return value

def box_fixnum(val):
    return tag_ptr(val, "fixnum")

def box_char(c):
    val = ord(c)    # Get ASCII value of character
    return tag_ptr(val, "char")

def box_bool(val):
    return tag_ptr(val, "bool")

def box_empty_list():
    return tag_ptr(0, "empty_list")

class Compiler:
    def __init__(self):
        self.code = []

    def compile(self, expr):
        emit = self.code.append
        match expr:
            case int():                 # Int
                emit(I.LOAD64)
                emit(box_fixnum(expr))
            case str():
                emit(I.LOAD64)
                if expr == "#t":        # Bool: T
                    emit(box_bool(0))
                elif expr == "#f":      # Bool: F
                    emit(box_bool(1))
                elif len(expr) == 1:    # Char
                    emit(box_char(expr))
            case list():
                if len(expr) == 0:      # Empty list
                    emit(I.LOAD64)
                    emit(box_empty_list())
    
    def compile_function(self, expr):
        self.compile(expr)
        self.code.append(I.RETURN)

    def write_to_stream(self, f):
        print(self.code)
        for op in self.code:
            f.write(op.to_bytes(8, "little"))

class I(enum.IntEnum):
    # Where all of our opcodes will go
    LOAD64 = enum.auto()
    RETURN = enum.auto()

import sys
def compile_program():
    source = sys.stdin.read()
    program = scheme_parse(source)
    compiler = Compiler()
    compiler.compile_function(program)
    compiler.write_to_stream(sys.stdout.buffer)

if __name__ == "__main__":
    compile_program()