import unittest
import enum

########### PARSER ##############

class Parser:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.length = len(source)

    def parse(self) -> object:
        self.skip_whitespace()
        match self.peek():
            case '':
                raise EOFError("Unexpected end of input")
            case c if c.isdigit():
                return self.parse_number()
            case c:
                raise NotImplementedError(f"Parser only supports numbers currently. Found {c}")
            
    def skip_whitespace(self):
        self.source = self.source.strip()
        self.length = len(self.source)

    def peek(self):
        return self.source[self.pos]

    def parse_number(self):
        start = self.pos
        while self.pos < self.length and self.source[self.pos].isdigit():
            self.pos += 1
        return int(self.source[start:self.pos])
    

def scheme_parse(source: str) -> object:
    return Parser(source).parse()

class ParseTests(unittest.TestCase):
    def _parse(self, source: str) -> object:
        return Parser(source).parse()

    def test_parse_fixnum(self):
        self.assertEqual(self._parse("42"), 42)

    def test_parse_fixnum_with_whitespace(self):
        self.assertEqual(self._parse("     42"), 42)

########### COMPILER ##############

class SI:
    def __init__(self, mask, tag, shift):
        self.mask = mask
        self.tag = tag
        self.shift = shift
SHIFT_INFO = {
    "fixnum": SI(mask=3, tag=0, shift=2)
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

class Compiler:
    def __init__(self):
        self.code = []

    def compile(self, expr):
        emit = self.code.append
        match expr:
            case int(_):
                emit(I.LOAD64)
                emit(box_fixnum(expr))
    
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