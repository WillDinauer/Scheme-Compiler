import unittest

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

class Compiler:
    def __init__(self):
        self.code = []

    def compile(self, expr):
        raise NotImplementedError("compile")

    def write_to_stream(self, f):
        raise NotImplementedError("write_to_stream")

import enum
class I(enum.IntEnum):
    # Where all of our opcodes will go
    pass

import sys
def compile_program():
    source = sys.stdin.read()
    program = scheme_parse(source)
    compiler = Compiler()
    compiler.compile_function(program)
    compiler.write_to_stream(sys.stdout)

if __name__ == "__main__":
    compile_program()