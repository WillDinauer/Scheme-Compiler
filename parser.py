import unittest

class Character:
    def __init__(self, c: str):
        self.c = c

    def get_char(self):
        return self.c

class Parser:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.length = len(source)

    def finished(self):
        return self.pos >= self.length

    def parse(self) -> object:
        self.skip_whitespace()
        if self.finished():
            return
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
                self.pos += 1
                return None
            case c if c.isascii():
                return self.parse_string()
            case c:
                raise NotImplementedError(f"Unhandled character {c}")
    
    # Increment the place in the file, raise error if reached EOF.
    def try_increment(self, err):
        self.pos += 1
        if self.finished():
            raise err
    
    # Look for a '|#' block. When the function is called, we assumed pos is at the '|' of the '#|' entry.
    # After this function concludes, pos will be placed AFTER the ending of the block '|#'.
    def skip_comment(self):
        err = SyntaxError("Unclosed comment block.")
        self.try_increment(err)
        while True:
            # Search for end of comment block
            if self.peek() == '|':
                self.try_increment(err)
                if self.peek() == '#':
                    self.pos += 1
                    return
            
            # Search for a nested comment block
            elif self.peek() == '#':
                self.try_increment(err)
                if self.peek() == '|':
                    # Recursive call
                    self.skip_comment()

            else:
                # We should never increment having not checked the char
                self.try_increment(err)
            
    def skip_whitespace(self):
        if self.finished():
            return
        
        while self.peek().isspace():
            self.pos += 1
            if self.pos >= self.length:
                return
        
         # Ignore comments
        if self.peek() == ';':
            while self.peek() != '\n':
                self.pos += 1
                if self.pos >= self.length:
                    return
            self.skip_whitespace()
            return
        
        # Ignore comment blocks
        if self.peek() == '#':
            self.try_increment(SyntaxError("Invalid character '#' at EOF."))
            if self.peek() == '|':
                # Guaranteed to place pos after end of comment block
                self.skip_comment()
                self.skip_whitespace()
            else:
                # Back up! We need to parse this '#' as non-whitespace
                self.pos -= 1

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
                self.pos += 1
                return True
            case 'f':
                self.pos += 1
                return False
    
    def parse_char(self):
        self.pos += 1
        val: str = self.parse_string()

        # Typical Characters
        if len(val) == 1 and val.isascii():
            return Character(val)
        
        # Special characters
        raise NotImplementedError(f"Special characters not currently supported. Found '#\{val}'")

    def parse_string(self) -> str:
        start = self.pos
        while self.pos < self.length and self.peek().isascii() and not self.peek().isspace() and not self.peek() == ')':
            self.pos += 1
        return self.source[start:self.pos]
    
    def parse_list(self):
        expr_list = []
        self.pos += 1
        # This works because recursive calls will consume their respective closing parens
        while (expr := self.parse()) != None: # ')' returns None
            expr_list.append(expr)
        return expr_list


def scheme_parse(source: str) -> object:
    expressions = []

    sp = Parser(source)
    while sp.pos < sp.length:
        expr = sp.parse()
        if expr:
            expressions.append(expr)
    return expressions

class ParseTests(unittest.TestCase):
    def _parse(self, source: str) -> object:
        return Parser(source).parse()

    def test_parse_fixnum(self):
        self.assertEqual(self._parse("42"), 42)

    def test_parse_fixnum_with_whitespace(self):
        self.assertEqual(self._parse("     42"), 42)

    def test_parse_true_bool(self):
        self.assertEqual(self._parse("#t"), True)

    def test_parse_false_bool(self):
        self.assertEqual(self._parse("#f"), False)

    def test_parse_character(self):
        self.assertEqual(self._parse("#\c").get_char(), Character("c").get_char())

    def test_parse_string(self):
        self.assertEqual(self._parse("add1"), "add1")

    def test_parse_expr(self):
        self.assertEqual(self._parse("(add1 2)"), ["add1", 2])

    def test_parse__nested_list(self):
        self.assertEqual(self._parse("(+ 2 (+ 3 4))"), ["+", 2, ["+", 3, 4]])

    def test_parse_multiple_nested_list(self):
        self.assertEqual(self._parse("(= (+ 1 2) (- 4 1))"), ["=", ["+", 1, 2], ["-", 4, 1]])

if __name__ == "__main__":
    unittest.main()