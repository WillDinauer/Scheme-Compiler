import enum
import sys
from parser import Character, scheme_parse

# We are assuming 64-bit
SYSTEM_TYPE =   64
OP_LEN =        8

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

    # Conditionals
    JMP = enum.auto() # jump
    JIF = enum.auto() # jump if false

# Container for shift/tagging information
class SI:
    def __init__(self, mask, tag, shift):
        self.mask = mask
        self.tag = tag
        self.shift = shift

# Mask/shift/tagging information for various types
SHIFT_INFO = {
    "fixnum": SI(mask=3, tag=0, shift=2),
    "char": SI(mask=255, tag=15, shift=8),
    "bool": SI(mask=127, tag=31, shift=7),
    "empty_list": SI(mask=255, tag=47, shift=0)    # EL value is the tag...?
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

    def update_environment(self, environment, ops, binding_list):
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
            ops += self.compile(binding[1])
        
        for key, value in environment.items():
            if key not in new_environment:
                # Update environment for previously allocated locals as well
                new_environment[key] = value + num_bindings
        
        return new_environment, ops


    def compile(self, expr, environment = {}) -> list:
        ops = []
        emit = ops.append
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
                # Empty list
                if len(expr) == 0:
                    emit(I.LOAD64)
                    emit(box_empty_list())
                
                # Function call
                func_name = expr[0]
                match func_name:
                    # Unary functions
                    case "add1":
                        ops += self.compile(expr[1], environment)
                        emit(I.ADD1)
                    case "sub1":
                        ops += self.compile(expr[1], environment)
                        emit(I.SUB1)
                    case "integer->char":
                        ops += self.compile(expr[1], environment)
                        emit(I.INT_TO_CHAR)
                    case "char->integer":
                        ops += self.compile(expr[1], environment)
                        emit(I.CHAR_TO_INT)
                    case "null?":
                        ops += self.compile(expr[1], environment)
                        emit(I.NULL_CHECK)
                    case "zero?":
                        ops += self.compile(expr[1], environment)
                        emit(I.ZERO_CHECK)
                    case "not":
                        ops += self.compile(expr[1], environment)
                        emit(I.NOT)
                    case "integer?":
                        ops += self.compile(expr[1], environment)
                        emit(I.INT_CHECK)
                    case "boolean?":
                        ops += self.compile(expr[1], environment)
                        emit(I.BOOL_CHECK)

                    # Binary functions
                    case "+":
                        ops += self.compile(expr[1])
                        ops += self.compile(expr[2])
                        emit(I.ADD)
                    case "-":
                        ops += self.compile(expr[1])
                        ops += self.compile(expr[2])
                        emit(I.SUB)
                    case "*":
                        ops += self.compile(expr[1])
                        ops += self.compile(expr[2])
                        emit(I.MUL)
                    case "<":
                        ops += self.compile(expr[1])
                        ops += self.compile(expr[2])
                        emit(I.LT)
                    case "=":
                        ops += self.compile(expr[1])
                        ops += self.compile(expr[2])
                        emit(I.EQL)

                    # Ternary functions
                    case "if":
                        # -- If --
                        ops += self.compile(expr[1])

                        # -- Else --
                        else_code = self.compile(expr[3])

                        # -- Then --
                        then_jump = [I.JMP, box_fixnum(len(else_code)) * OP_LEN]
                        then_code = self.compile(expr[2]) + then_jump

                        # Potential jump to Else
                        emit(I.JIF)
                        emit(box_fixnum(len(then_code)) * OP_LEN)
                        
                        # Then code (with jump)
                        ops += then_code

                        # Else code
                        ops += else_code

                    # n-ary functions
                    case "let":
                        bindings = expr[1]
                        environment, ops = self.update_environment(environment, ops, bindings)
                        sub_expressions = expr[2:]
                        for sub_expr in sub_expressions:
                            ops += self.compile(sub_expr, environment)
                        
                        # Drop unused return values AND tear down locals
                        for _ in range(len(bindings) + len(sub_expressions) - 1):
                            emit(I.SQUASH)

                    case _:
                        raise SyntaxError(f"Compiler raised error: calling '{func_name}' as a function is not permitted.")
                        

            case str():
                # Local variables
                if expr in environment:
                    # Duplicate their value onto the top of the stack
                    emit(I.GET)
                    emit(box_fixnum(environment[expr]))
                else:
                    raise SyntaxError(f"Compiler raised error: use of undefined variable/function '{expr}'")
        return ops
    
    def compile_function(self, expr, last=True):
        self.code += self.compile(expr)
        last_op = I.RETURN if last else I.DROP
        self.code.append(last_op)

    def write_to_stream(self, f):
        print(self.code)
        for op in self.code:
            f.write(op.to_bytes(OP_LEN, "little"))

def compile_program():
    # Parse the Scheme file (from stdin)
    source = sys.stdin.read()
    program = scheme_parse(source)

    # Compile all functions at the root of the file
    compiler = Compiler()
    for i, function in enumerate(program):
        last = i == len(program) - 1
        compiler.compile_function(function, last)

    # Write the code out
    compiler.write_to_stream(sys.stdout.buffer)

if __name__ == "__main__":
    compile_program()