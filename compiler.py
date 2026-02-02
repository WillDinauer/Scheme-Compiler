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
    FINISH = enum.auto()

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

    # Vector
    ALLOC_VEC = enum.auto()
    VEC_REF = enum.auto()
    VEC_SET = enum.auto()
    VEC_APPEND = enum.auto()

    # Function calls
    FUNCALL = enum.auto()
    RETURN = enum.auto()

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
        raise ValueError(f"{LOG_TAG}: {type} value {value} too large to store")
    
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
        error_msg = f"Invalid usage of function '{expr[0]}': {num_args} args expected."
        compiler_error(error_msg)

class Compiler:
    def __init__(self):
        self.code = []

    def create_new_environment(self, environment, binding_list) -> dict:
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
            self.compile(binding[1], environment)
        
        for key, value in environment.items():
            if key not in new_environment:
                # Update environment for previously allocated locals as well
                new_environment[key] = value + num_bindings
        
        return new_environment

    def update_indices(self, environment, shift) -> dict:
        new_environment = environment.copy()
        for local in new_environment:
            new_environment[local] += shift
        return new_environment
    
    def compile_list(self, elements, opcode, environment):
        # Traverse over args in reverse order (to pop them in order)
        for i in range(len(elements) - 1, -1, -1):
            el = elements[i]
            self.compile(el, self.update_indices(environment, len(elements) - 1 - i))

        # Add particular opcode for this operation
        self.code.append(opcode)
        self.code.append(box_fixnum(len(elements)))
    
    def compile_vector(self, elements, environment):
        self.compile_list(elements, I.ALLOC_VEC, environment)
    
    def compile_string(self, char_arr, environment):
        self.compile_list(char_arr, I.ALLOC_STR, environment)
    
    def general_fn_emit(self, expr, n_args, opcode, environment):
        validate_args(expr, n_args)
        # Compile args
        for i, sub_expr in enumerate(expr[1:]):
            self.compile(sub_expr, self.update_indices(environment, i))
        # Add specific opcode
        self.code.append(opcode)
    
    def compile_subexprs(self, sub_expressions, environment):
        for i, sub_expr in enumerate(sub_expressions):
            self.compile(sub_expr, environment)

            # Drop unused values
            if i < len(sub_expressions) - 1:
                self.code.append(I.DROP)
        
    def compile(self, expr, environment) -> list:
        emit = self.code.append
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
                self.compile_string(char_arr, environment)
            case list():
                # Empty list
                if len(expr) == 0:
                    emit(I.LOAD64)
                    emit(box_empty_list())
                    return

                # List as a function call (only lambda can do this atm)
                if isinstance(expr[0], list):
                    # Make the function call
                    self.compile_function(expr, self.update_indices(environment, 1))
                    return
                
                # Function call
                func_name = expr[0]
                if func_name in environment:
                    self.compile_function(expr, environment)
                    return

                match func_name:
                    # Unary functions
                    case "add1":
                        self.general_fn_emit(expr, 1, I.ADD1, environment)
                    case "sub1":
                        self.general_fn_emit(expr, 1, I.SUB1, environment)
                    case "integer->char":
                        self.general_fn_emit(expr, 1, I.INT_TO_CHAR, environment)
                    case "char->integer":
                        self.general_fn_emit(expr, 1, I.CHAR_TO_INT, environment)
                    case "null?":
                        self.general_fn_emit(expr, 1, I.NULL_CHECK, environment)
                    case "zero?":
                        self.general_fn_emit(expr, 1, I.ZERO_CHECK, environment)
                    case "not":
                        self.general_fn_emit(expr, 1, I.NOT, environment)
                    case "integer?":
                        self.general_fn_emit(expr, 1, I.INT_CHECK, environment)
                    case "boolean?":
                        self.general_fn_emit(expr, 1, I.BOOL_CHECK, environment)

                    # Pair functions
                    case "car":
                        self.general_fn_emit(expr, 1, I.CAR, environment)
                    case "cdr":
                        self.general_fn_emit(expr, 1, I.CDR, environment)
                    case "cons":
                        self.general_fn_emit(expr, 2, I.CONS, environment)

                    # Binary functions
                    case "+":
                        self.general_fn_emit(expr, 2, I.ADD, environment)
                    case "-":
                        self.general_fn_emit(expr, 2, I.SUB, environment)
                    case "*":
                        self.general_fn_emit(expr, 2, I.MUL, environment)
                    case "<":
                        self.general_fn_emit(expr, 2, I.LT, environment)
                    case "=":
                        self.general_fn_emit(expr, 2, I.EQL, environment)

                    # Ternary functions
                    case "if":
                        validate_args(expr, 3)
                        # -- If --
                        self.compile(expr[1], environment)
                        emit(I.JIF)
                        # Placeholder jump length
                        emit(box_fixnum(0))
                        ckpt1 = len(self.code)

                        # -- Then -- 
                        self.compile(expr[2], environment)
                        emit(I.JMP)
                        emit(box_fixnum(0))
                        ckpt2 = len(self.code)

                        # -- Else --
                        self.compile(expr[3], environment)
                        ckpt3 = len(self.code)
                        
                        # Update placeholder values
                        self.code[ckpt1-1] = box_fixnum((ckpt2 - ckpt1) * OP_LEN)
                        self.code[ckpt2-1] = box_fixnum((ckpt3 - ckpt2) * OP_LEN)

                    # n-ary functions
                    case "let":
                        form_error_str = f"'let' must be of form: (let ((symbol_1 value_2) ... (symbol_n value_n)) expr_1 ... expr_n)"
                        # Check length of expression
                        if len(expr) < 3:
                            compiler_error(form_error_str)
                        bindings = expr[1]
                        
                        # Handle bindings
                        environment = self.create_new_environment(environment, bindings)
                        
                        # Compile all sub expressions
                        sub_expressions = expr[2:]
                        self.compile_subexprs(sub_expressions, environment)
                        
                        # Tear down local variables
                        for _ in range(len(bindings)):
                            emit(I.SQUASH)
                    case "begin":
                        # Compile all subexpressions
                        sub_expressions = expr[1:]
                        self.compile_subexprs(sub_expressions, environment)
                    
                    # String functions
                    case "string":
                        self.compile_string(expr[1:], environment)
                    case "string-ref":
                        self.general_fn_emit(expr, 2, I.STR_REF, environment)
                    case "string-set!":
                        self.general_fn_emit(expr, 3, I.STR_SET, environment)
                    case "string-append":
                        self.compile_list(expr[1:], I.STR_APPEND, environment)

                    # Vector functions
                    case "vector":
                        self.compile_vector(expr[1:], environment)
                    case "vector-ref":
                        self.general_fn_emit(expr, 2, I.VEC_REF, environment)
                    case "vector-set!":
                        self.general_fn_emit(expr, 3, I.VEC_SET, environment)
                    case "vector-append":
                        self.compile_list(expr[1:], I.VEC_APPEND, environment)


                    case _:
                        compiler_error(f"Calling unbound/undefined '{func_name}' as a function.")
                        

            case str():
                # Local variables
                if expr in environment:
                    # Duplicate their value onto the top of the stack
                    emit(I.GET)
                    emit(box_fixnum(environment[expr]))
                else:
                    compiler_error(f"Use of undefined variable '{expr}'")
    
    def compile_function(self, expr, environment):
        args = expr[1:]
        # Compile args
        for i, arg in enumerate(args):
            self.compile(arg, self.update_indices(environment, i))

        # Load lambda or function call
        self.compile(expr[0], self.update_indices(len(args)))

        self.code.append(I.FUNCALL)

        self.code.append(I.RETURN)

    def write_to_stream(self, f):
        # human-readable
        with open("code.txt", 'w') as code_file:
            print(self.code, file=code_file)

        # print bytes
        for op in self.code:
            f.write(op.to_bytes(OP_LEN, "little"))
    
    def drop_return_value(self):
        self.code.append(I.DROP)

    def finish(self):
        self.code.append(I.FINISH)

def compile_program():
    # Parse the Scheme file (from stdin)
    source = sys.stdin.read()
    program = scheme_parse(source)

    # Compile all functions at the root of the file
    compiler = Compiler()
    for i, function in enumerate(program):
        compiler.compile(function, {})

        # Drop value (except for the last function)
        if i < len(program) - 1:
            compiler.drop_return_value()

    # Last value should be returned for display
    compiler.finish()

    # Write the code out
    compiler.write_to_stream(sys.stdout.buffer)

if __name__ == "__main__":
    compile_program()