import unittest

class Character:
    def __init__(self, c: str):
        self.c = c

    def get_char(self):
        return self.c

    def to_string(self):
        return self.get_char()

# Strings are just an array of characters
class String:
    def __init__(self, char_array):
        self.char_array = char_array

    def get_characters(self):
        return self.char_array
    
    def to_string(self):
        result = ""
        for c in self.char_array:
            result += c.to_string()
        return result
    
class List:
    def __init__(self, elements):
        self.elements = elements
    
    def get_elements(self):
        return self.elements
    
    def to_string(self):
        result = ""
        for e in self.elements:
            result += e.to_string()
        return result
    
class Symbol:
    def __init__(self, symbol):
        self.symbol = symbol
        self.char_array = [Character(c) for c in symbol]

    def get_characters(self):
        return self.char_array
    
    def to_string(self):
        result = ""
        for e in self.char_array:
            result += e.to_string()
        return result
    
class EmptyList:
    def __init__(self):
        pass

    def to_string(self):
        return "EmptyList"

class Parser:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.length = len(source)

    def finished(self):
        return self.pos >= self.length
    
    # Increment the place in the file, raise error if reached EOF.
    def try_increment(self, err):
        self.pos += 1
        if self.finished():
            raise err
        
    def is_empty(self):
        self.skip_whitespace()
        return self.finished()

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
                return self.parse_subexpr()
            case ')':
                self.pos += 1
                return None
            case '\'':
                return self.parse_quoted()
            case '\"':
                return self.parse_string()
            case c if c.isascii():
                return self.parse_symbol()
            case c:
                raise NotImplementedError(f"Unhandled character {c}")
        
    def is_delim(self, c):
        return c.isspace() or c == ')' or c == '('
    
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
        self.try_increment(SyntaxError("Trying to parse special..."))

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
            case _:
                raise SyntaxError("Invalid or unimplemented special character")
            
    def parse_quoted(self):
        self.try_increment(SyntaxError("Trying to parse quoted..."))

        match self.peek():
            case '':
                raise EOFError("Unexpected end of input")
            case '(':
                return self.parse_list()
            case _:
                RuntimeError("Quoting currently unimplemented.")
            
    
    def parse_list(self):
        self.try_increment(SyntaxError("Failure while trying to parse list"))

        if self.peek() == ')':
            self.pos += 1
            return EmptyList()

        raise RuntimeError("Non-empty quoted lists are currently unimplemented.")

    
    def parse_char(self):
        self.pos += 1
        val: str = self.parse_symbol()

        # Typical Characters
        if len(val) == 1 and val.isascii():
            return Character(val)
        
        # Special characters
        match val:
            case "space":
                return Character(' ')
            case "newline":
                return Character('\n')
            case "tab":
                return Character('\t')
        raise NotImplementedError(f"Invalid or unsupported character. Found '#\{val}'")
    
    def parse_string(self) -> str:
        syntax_err = SyntaxError("Parsing error - unterminated string")
        self.try_increment(syntax_err)
        chars = []
        # Check for un-escaped quotes
        escaped = False

        while escaped or (not self.peek() == '\"'):
            # Match on special escaped characters
            if escaped:
                match self.peek():
                    case 'n':
                        chars.append(Character('\n'))
                    case 't':
                        chars.append(Character('\t'))
                    case '"':
                        chars.append(Character('\"'))
                    case '\\':
                        chars.append(Character('\\'))
                    case '\'':
                        chars.append(Character('\''))
                    case _:
                        raise SyntaxError(f"Unknown/unhandled escaped character in string: {self.peek()}")
                escaped = False
            # Check for escape character
            elif self.peek() == '\\':
                escaped = True
            # Not escaped, just append character
            else:
                chars.append(Character(self.peek()))
            self.try_increment(syntax_err)
        self.pos += 1
        return String(chars)

    def parse_symbol(self) -> str:
        start = self.pos
        while self.pos < self.length and self.peek().isascii() and not self.is_delim(self.peek()):
            self.pos += 1
        return self.source[start:self.pos]
    
    def parse_subexpr(self):
        expr_list = []
        self.pos += 1
        # This works because recursive calls will consume their respective closing parens
        while (expr := self.parse()) != None: # ')' returns None
            expr_list.append(expr)
        return expr_list
    
def is_empty(source):
    sp = Parser(source)
    return sp.is_empty()

scheme_simple_library = {
    "+": "(lambda (x y) (+ x y))",
    "-": "(lambda (x y) (- x y))",
    "*": "(lambda (x y) (* x y))",
    "cons": "(lambda (x y) (cons x y))",
}

scheme_rec_library = {
    "map": "(lambda (x y) (if (null? y) y (cons (x (car y)) (map x (cdr y)))))",
    "foldl": "(lambda (f acc l) (if (null? l) acc (foldl f (f (car l) acc) (cdr l))))",
    "foldr": "(lambda (f acc l) (if (null? l) acc (f (car l) (foldr f acc (cdr l)))))"
}

def add_bindings(library: dict):
    res = ""
    for i, (key, value) in enumerate(library.items()):
        binding = "(" + key + " " + value + ")"

        # Spaces between bindings
        if i != len(scheme_rec_library) - 1:
            binding += " "
        res += binding
    return res

def construct_simple_header():
    header = "(let (" + add_bindings(scheme_simple_library) + ") "
    return header

def construct_rec_header():
    header = "(letrec (" + add_bindings(scheme_rec_library) + ") "
    return header

def construct_header():
    return construct_rec_header()

def scheme_parse(source: str) -> object:
    # Special case empty file
    if is_empty(source):
        return
    
    source = construct_header() + source + ")"
    sp = Parser(source)
    expr = sp.parse()
    return expr

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
        self.assertEqual(self._parse("#\c").to_string(), Character("c").to_string())

    def test_parse_symbol(self):
        self.assertEqual(self._parse("add1"), "add1")

    def test_parse_expr(self):
        self.assertEqual(self._parse("(add1 2)"), ["add1", 2])

    def test_parse_nested_list(self):
        self.assertEqual(self._parse("(+ 2 (+ 3 4))"), ["+", 2, ["+", 3, 4]])

    def test_parse_multiple_nested_list(self):
        self.assertEqual(self._parse("(= (+ 1 2) (- 4 1))"), ["=", ["+", 1, 2], ["-", 4, 1]])

    def test_parse_string(self):
        result = self._parse("(string-append \"ab\" \"cd\")")
        result[1] = result[1].to_string()
        result[2] = result[2].to_string()
        self.assertEqual(result, ["string-append", String([Character('a'), Character('b')]).to_string(), String([Character('c'), Character('d')]).to_string()])

    def test_parse_complex_string(self):
        result = self._parse("(string-append \"a\\\"\" \"c\\\"\\\"\")")
        result[1] = result[1].to_string()
        result[2] = result[2].to_string()
        self.assertEqual(result, ["string-append", String([Character('a'), Character('\"')]).to_string(), String([Character('c'), Character('\"'), Character('\"')]).to_string()])
    

if __name__ == "__main__":
    unittest.main()