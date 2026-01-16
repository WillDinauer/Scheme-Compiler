import enum
from parser import Character

# We are assuming 64-bit
SYSTEM_TYPE = 64

# Opcodes
class I(enum.IntEnum):
    LOAD64 = enum.auto()
    RETURN = enum.auto()

    # Unary functions
    ADD1 = enum.auto()
    SUB1 = enum.auto()
    INT_TO_CHAR = enum.auto()
    CHAR_TO_INT = enum.auto()
    NULL_CHECK = enum.auto()
    ZERO_CHECK = enum.auto()
    INT_CHECK = enum.auto()
    BOOL_CHECK = enum.auto()
    NOT = enum.auto()
    
    # Binary functions
    ADD = enum.auto()
    SUB = enum.auto()
    MUL = enum.auto()
    LT = enum.auto()
    EQL = enum.auto()

    # Local variables
    GET = enum.auto()
    DROP = enum.auto()
    SQUASH = enum.auto()

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

    def update_environment(self, environment, binding_list):
        emit = self.code.append
        num_bindings = len(binding_list)
        new_environment = {}
        
        # iterate through bindings
        for i, binding in enumerate(binding_list):
            variable_name = binding[0]

            # Validate binding variable
            if not isinstance(variable_name, str):
                raise ValueError(f"Bad let: Trying to bind non-str variable {variable_name}")
            if variable_name in new_environment:
                raise RuntimeError(f"Bad let: Var {variable_name} being bound twice in single let expr.")
            new_environment[variable_name] = num_bindings - i - 1   # Sub 1 to 0-index

            # Bindings take 1 argument (their value)
            self.compile(binding[1])
        
        for key, value in environment.items():
            if key not in new_environment:
                # Update environment for previously allocated locals as well
                new_environment[key] = value + num_bindings
        
        return new_environment


    def compile(self, expr, environment = {}):
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
                        self.compile(expr[1], environment)
                        emit(I.ADD1)
                    case "sub1":
                        self.compile(expr[1], environment)
                        emit(I.SUB1)
                    case "integer->char":
                        self.compile(expr[1], environment)
                        emit(I.INT_TO_CHAR)
                    case "char->integer":
                        self.compile(expr[1], environment)
                        emit(I.CHAR_TO_INT)
                    case "null?":
                        self.compile(expr[1], environment)
                        emit(I.NULL_CHECK)
                    case "zero?":
                        self.compile(expr[1], environment)
                        emit(I.ZERO_CHECK)
                    case "not":
                        self.compile(expr[1], environment)
                        emit(I.NOT)
                    case "integer?":
                        self.compile(expr[1], environment)
                        emit(I.INT_CHECK)
                    case "boolean?":
                        self.compile(expr[1], environment)
                        emit(I.BOOL_CHECK)

                    # Binary functions
                    case "+":
                        self.compile(expr[1])
                        self.compile(expr[2])
                        emit(I.ADD)
                    case "-":
                        self.compile(expr[1])
                        self.compile(expr[2])
                        emit(I.SUB)
                    case "*":
                        self.compile(expr[1])
                        self.compile(expr[2])
                        emit(I.MUL)
                    case "<":
                        self.compile(expr[1])
                        self.compile(expr[2])
                        emit(I.LT)
                    case "=":
                        self.compile(expr[1])
                        self.compile(expr[2])
                        emit(I.EQL)

                    # n-ary functions
                    case "let":
                        bindings = expr[1]
                        environment = self.update_environment(environment, bindings)
                        for sub_expr in expr[2:]:
                            self.compile(sub_expr, environment)
                        for _ in range(len(bindings)):
                            emit(I.SQUASH)
                        

            case str():
                if expr in environment:
                    emit(I.GET)
                    emit(box_fixnum(environment[expr]))
                
    
    def compile_function(self, expr):
        self.compile(expr)
        self.code.append(I.RETURN)

    def write_to_stream(self, f):
        print(self.code)
        for op in self.code:
            f.write(op.to_bytes(8, "little"))