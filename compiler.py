import enum
from parser import Character

# We are assuming 64-bit
SYSTEM_TYPE = 64

# Opcodes
class I(enum.IntEnum):
    LOAD64 = enum.auto()
    RETURN = enum.auto()
    ADD1 = enum.auto()
    SUB1 = enum.auto()
    INT_TO_CHAR = enum.auto()
    CHAR_TO_INT = enum.auto()
    NULL_CHECK = enum.auto()
    ZERO_CHECK = enum.auto()
    INT_CHECK = enum.auto()
    BOOL_CHECK = enum.auto()
    NOT = enum.auto()

# Container for shift/tagging information
class SI:
    def __init__(self, mask, tag, shift):
        self.mask = mask
        self.tag = tag
        self.shift = shift

# Mask/shift/tagging information for various types
SHIFT_INFO = {
    "fixnum": SI(mask=(1<<2)-1, tag=0, shift=2),
    "char": SI(mask=(1<<9)-1, tag=(1<<5)-1, shift=8),
    "bool": SI(mask=(1<<8)-1, tag=(1<<6)-1, shift=7),
    "empty_list": SI(mask=(1<<9)-1, tag=47, shift=0)    # EL value is the tag...?
}

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
            case bool():
                emit(I.LOAD64)
                if expr:                # Bool: T
                    emit(box_bool(0))
                else:                   # Bool: F
                    emit(box_bool(1))
            case Character():           # Char
                emit(I.LOAD64)
                emit(box_char(expr.get_char()))
            case list():
                if len(expr) == 0:      # Empty list
                    emit(I.LOAD64)
                    emit(box_empty_list())
                
                # Function call
                func_name = expr[0]
                match func_name:
                    # Unary functions
                    case "add1":
                        self.compile(expr[1])
                        emit(I.ADD1)
                    case "sub1":
                        pass
                    case "integer->char":
                        pass
                    case "char->integer":
                        pass
                    case "null?":
                        pass
                    case "zero?":
                        pass
                    case "not":
                        pass
                    case "integer?":
                        pass
                    case "boolean?":
                        pass

                    # Binary functions
                    case "+":
                        pass
                    case "-":
                        pass
                    case "*":
                        pass
                    case "<":
                        pass
                    case "=":
                        pass

            case str():
                pass
                
    
    def compile_function(self, expr):
        self.compile(expr)
        self.code.append(I.RETURN)

    def write_to_stream(self, f):
        print(self.code)
        for op in self.code:
            f.write(op.to_bytes(8, "little"))