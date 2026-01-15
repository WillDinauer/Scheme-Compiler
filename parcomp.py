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
            case '#':
                return self.parse_special()
            case '(':
                pass
            case ')':
                pass
            case c:
                raise NotImplementedError(f"Parser found something (currently) unsupported: {c}")
            
    def skip_whitespace(self):
        self.source = self.source.strip()
        self.length = len(self.source)

    def peek(self):
        return self.source[self.pos]

    def parse_number(self):
        start = self.pos
        while self.pos < self.length and self.peek().isdigit():
            self.pos += 1
        return int(self.source[start:self.pos])
    
    def parse_special(self):
        self.pos += 1
        match self.peek():
            case '':
                raise EOFError("Unexpected end of input")
            case '\\':
                return self.parse_char()
            case 't':
                return True
            case 'f':
                return False
    
    def parse_char(self):
        self.pos += 1
        val: str = self.parse_string()

        # Typical Characters
        if len(val) == 1 and val.isalpha():
            return val
        
        # Special characters
        raise NotImplementedError(f"Special characters not currently supported. Found {val}")

    def parse_string(self) -> str:
        start = self.pos
        while self.pos < self.length and self.peek().isalpha():
            self.pos += 1
        return self.source[start:self.pos]
        
    

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