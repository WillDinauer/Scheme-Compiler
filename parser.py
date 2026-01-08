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
        pass

    def peek(self):
        pass

def scheme_parse(source: str) -> object:
    return Parser(source).parse()

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