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
            case '#':
                return self.parse_special()
            case '(':
                return self.parse_list()
            case ')':
                pass
            case c if c.isalpha():
                return self.parse_string()
            case c:
                raise NotImplementedError(f"Unhandled character {c}")
            
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