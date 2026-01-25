import enum
import sys
from parser import scheme_parse, Character, String

LOG_TAG = "[COMPILER]"

# We are assuming 64-bit
SYSTEM_TYPE =   64
OP_LEN =        8
T_BOOL_VAL =    1
F_BOOL_VAL =    0
BYTE_LEN =      8

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

    # Cons
    CONS = enum.auto()
    CAR = enum.auto()
    CDR = enum.auto()

    # String
    ALLOC_STR = enum.auto()
    STR_REF = enum.auto()
    STR_SET = enum.auto()
    STR_APPEND = enum.auto()

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

def compiler_error(msg):
    raise SyntaxError(f"{LOG_TAG}: {msg}")

def validate_args(expr, num_args):
    if num_args != len(expr[1:]):
        error_msg = f"Invalid usage of function '{expr[0]}' - {num_args} args expected."
        compiler_error(error_msg)

class Compiler:
    def __init__(self):
        self.code = []

    def create_new_environment(self, environment, ops, binding_list) -> tuple[dict, list]:
        num_bindings = len(binding_list)
        new_environment = {}

        # binding list must be a list
        if not isinstance(binding_list, list):
            compiler_error(f"Bad let: Binding list is not a list - {binding_list}")
        
        # iterate through bindings
        for i, binding in enumerate(binding_list):
            # Validate individual binding
            if not isinstance(binding, list) or len(binding) != 2:
                compiler_error(f"Bad let: Invalid binding '{binding}' - bindings are of form (symbol value)")
            variable_name = binding[0]

            # Validate binding variable
            if not isinstance(variable_name, str):
                compiler_error(f"Bad let: Trying to bind non-str variable '{variable_name}'")
            if variable_name in new_environment:
                compiler_error(f"Bad let: local variable '{variable_name}' being bound twice in single let expr.")
            new_environment[variable_name] = num_bindings - i - 1   # Sub 1 to 0-index

            # Bindings take 1 argument (their value)
            ops += self.compile(binding[1], environment)
        
        for key, value in environment.items():
            if key not in new_environment:
                # Update environment for previously allocated locals as well
                new_environment[key] = value + num_bindings
        
        return new_environment, ops

    def update_indices(self, environment, shift) -> dict:
        new_environment = environment.copy()
        for local in new_environment:
            new_environment[local] += shift
        return new_environment
    
    def compile_string(self, char_arr, environment):
        ops = []
        length = len(char_arr)

        # Compile all characters (in reverse order, for stack purposes)
        for i in range(len(char_arr) - 1, -1, -1):
            c = char_arr[i]
            ops += self.compile(c, self.update_indices(environment, len(char_arr) - 1 - i))

        # Consume the characters on the stack to create a string
        ops.append(I.ALLOC_STR)
        ops.append(box_fixnum(length))

        return ops
        

    def compile(self, expr, environment) -> list:
        ops = []
        emit = ops.append
        match expr:
            case bool():
                emit(I.LOAD64)
                if expr:                # Bool: T
                    emit(box_bool(T_BOOL_VAL))
                else:                   # Bool: F
                    emit(box_bool(F_BOOL_VAL))
            case int():                 # Int
                emit(I.LOAD64)
                emit(box_fixnum(expr))
            case Character():           # Char
                emit(I.LOAD64)
                emit(box_char(expr.to_string()))
            case String():
                char_arr = expr.get_characters()
                ops += self.compile_string(char_arr, environment)
            case list():
                # Empty list
                if len(expr) == 0:
                    emit(I.LOAD64)
                    emit(box_empty_list())
                    return ops
                
                # Function call
                func_name = expr[0]
                if func_name in environment:
                    # TODO: this might change as we add additional functionality
                    raise SyntaxError(f"invalid use of local variable '{func_name}' as function")

                match func_name:
                    # Unary functions
                    case "add1":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.ADD1)
                    case "sub1":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.SUB1)
                    case "integer->char":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.INT_TO_CHAR)
                    case "char->integer":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.CHAR_TO_INT)
                    case "null?":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.NULL_CHECK)
                    case "zero?":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.ZERO_CHECK)
                    case "not":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.NOT)
                    case "integer?":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.INT_CHECK)
                    case "boolean?":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.BOOL_CHECK)

                    case "car":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.CAR)
                    case "cdr":
                        validate_args(expr, 1)
                        ops += self.compile(expr[1], environment)
                        emit(I.CDR)

                    # Binary functions
                    case "+":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.ADD)
                    case "-":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.SUB)
                    case "*":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.MUL)
                    case "<":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.LT)
                    case "=":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.EQL)

                    case "cons":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.CONS)

                    # Ternary functions
                    case "if":
                        validate_args(expr, 3)
                        # -- If --
                        ops += self.compile(expr[1], environment)

                        # -- Else --
                        else_code = self.compile(expr[3], environment)

                        # -- Then --
                        then_jump = [I.JMP, box_fixnum(len(else_code)) * OP_LEN]
                        then_code = self.compile(expr[2], environment) + then_jump

                        # Potential jump to Else
                        emit(I.JIF)
                        emit(box_fixnum(len(then_code)) * OP_LEN)
                        
                        # Then code (with jump)
                        ops += then_code

                        # Else code
                        ops += else_code

                    # n-ary functions
                    case "let":
                        form_error_str = f"'let' must be of form: (let ((symbol_1 value_2) ... (symbol_n value_n)) expr_1 ... expr_n)"
                        # Check length of expression
                        if len(expr) < 3:
                            compiler_error(form_error_str)
                        bindings = expr[1]
                        
                        # Handle bindings
                        environment, ops = self.create_new_environment(environment, ops, bindings)
                        
                        # Compile all sub expressions
                        sub_expressions = expr[2:]
                        for i, sub_expr in enumerate(sub_expressions):
                            ops += self.compile(sub_expr, environment)
                            
                            # Drop unused return values
                            if i < len(sub_expressions) - 1:
                                emit(I.DROP)
                        
                        # Tear down local variables
                        for _ in range(len(bindings)):
                            emit(I.SQUASH)
                    
                    # String functions
                    case "string":
                        ops += self.compile_string(expr[1:])
                    case "string-ref":
                        validate_args(expr, 2)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        emit(I.STR_REF)
                    case "string-set!":
                        validate_args(expr, 3)
                        ops += self.compile(expr[1], environment)
                        ops += self.compile(expr[2], self.update_indices(environment, 1))
                        ops += self.compile(expr[3], self.update_indices(environment, 2))
                        emit(I.STR_SET)
                    case "string-append":
                        strs = expr[1:]
                        for i in range(len(strs) - 1, -1, -1):
                            s = strs[i]
                            ops += self.compile(s, self.update_indices(environment, i))
                        emit(I.STR_APPEND)
                        emit(box_fixnum(len(strs)))
                        

                    case _:
                        compiler_error(f"Calling unbound/undefined '{func_name}' as a function.")
                        

            case str():
                # Local variables
                if expr in environment:
                    # Duplicate their value onto the top of the stack
                    emit(I.GET)
                    emit(box_fixnum(environment[expr]))
                else:
                    compiler_error(f"Use of undefined variable/function '{expr}'")
        return ops
    
    def compile_function(self, expr):
        self.code += self.compile(expr, {})

    def write_to_stream(self, f):
        # human-readable
        with open("code.txt", 'w') as code_file:
            print(self.code, file=code_file)

        # print bytes
        for op in self.code:
            f.write(op.to_bytes(OP_LEN, "little"))
    
    def drop_return_value(self):
        self.code.append(I.DROP)

    def add_ret(self):
        self.code.append(I.RETURN)

def compile_program():
    # Parse the Scheme file (from stdin)
    source = sys.stdin.read()
    program = scheme_parse(source)

    # Compile all functions at the root of the file
    compiler = Compiler()
    for i, function in enumerate(program):
        compiler.compile_function(function)

        # Drop value (except for the last function)
        if i < len(program) - 1:
            compiler.drop_return_value()

    # Last value should be returned
    compiler.add_ret()

    # Write the code out
    compiler.write_to_stream(sys.stdout.buffer)

if __name__ == "__main__":
    compile_program()