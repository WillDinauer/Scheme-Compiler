import enum
import sys
from parser import scheme_parse, Character, String, EmptyList

LOG_TAG = "[COMPILER]"

BUILTINS = {
    "integer->char", "char->integer", 
    "null?", "zero?", "not", "integer?", "boolean?", 
    "car", "cdr", "cons",
    "add1", "sub1", "+", "-", "*", "<", "=", 
    "if", "let", "begin", 
    "string", "string-ref", "string-set!", "string-append", 
    "vector", "vector-ref", "vector-set!", "vector-append", 
    "lambda"
}

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
    KLEG = enum.auto()

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

    # CLOSURE
    ALLOC_CLO = enum.auto()
    GET_CLOSURE = enum.auto()

    # Function calls
    FUNCALL = enum.auto()
    TAILCALL = enum.auto()
    RETURN = enum.auto()

    # Unspecified
    PUSH_UNSPEC = enum.auto()

# Environment item types
class EIT(enum.IntEnum):
    DEFAULT=enum.auto()
    FREE_VAR=enum.auto()
    CLOSURE=enum.auto()

class EnvItem:
    def __init__(self, position, type=EIT.DEFAULT):
        self.position = position
        self.type = type
    
    def shift(self, shift_amt):
        self.position += shift_amt

    def copy(self):
        return EnvItem(self.position, self.type)

# Container for shift/tagging information
class SI:
    def __init__(self, mask, tag, shift):
        self.mask = mask
        self.tag = tag
        self.shift = shift

class LET_TYPE(enum.IntEnum):
    DEFAULT=enum.auto()
    REC=enum.auto()
    STAR=enum.auto()

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

def validate_let(expr):
    form_error_str = f"'let' must be of form: (let ((symbol_1 value_2) ... (symbol_n value_n)) expr_1 ... expr_n)"
    # Check length of expression
    if len(expr) < 3:
        compiler_error(form_error_str)

    binding_list = expr[1]
    if not isinstance(binding_list, list):
            compiler_error(f"Bad let: Binding list is not a list - {binding_list}")
    bound = set()
        
    # iterate through bindings
    for binding in binding_list:
    # Validate individual binding
        if not isinstance(binding, list) or len(binding) != 2:
            compiler_error(f"Bad let: Invalid binding '{binding}' - bindings are of form (symbol value)")
        variable_name = binding[0]

        # Validate binding variable
        if not isinstance(variable_name, str):
            compiler_error(f"Bad let: Trying to bind non-str variable '{variable_name}'")
        if variable_name in bound:
            compiler_error(f"Bad let: local variable '{variable_name}' being bound twice in single let expr.")
        bound.add(variable_name)
    
    return bound

class Compiler:
    def __init__(self):
        self.code = []

    # This function assumes we have already validated the let (with a call to 'validate_let')
    def create_let_environment(self, environment, binding_list) -> dict:
        num_bindings = len(binding_list)
        new_environment = {}

        # iterate through bindings
        for i, binding in enumerate(binding_list):
            variable_name = binding[0]
            new_environment[variable_name] = EnvItem(num_bindings - i - 1)  # Subtract 1 to 0-index

            # Bindings take 1 argument (their value/expr)
            self.compile(binding[1], environment)
        
        for key, value in environment.items():
            if key not in new_environment:
                # Update environment for previously allocated locals as well
                new_environment[key] = value.copy()
                new_environment[key].shift(num_bindings)
        
        return new_environment
    
    def create_letrec_environment(self, environment, binding_list) -> dict:
        # Note...this check is for letrec taking a temporary single arg
        num_bindings = len(binding_list)
        if num_bindings != 1:
            compiler_error(f"letrec must have a single binding at the moment (received {num_bindings})")
        new_environment = {}

        # Add the binding to the environment
        binding = binding_list[0]
        lambda_name = binding[0]
        expr = binding[1]

        # Compile the binding - this is assumed to be a lambda
        self.compile_rec_lambda(expr, lambda_name, environment)

        # Add binding and shift existing environment by 1 for new binding
        new_environment[lambda_name] = EnvItem(0)
        for key, value in environment.items():
            new_environment[key] = value.copy()
            new_environment[key].shift(num_bindings)

        return new_environment
    
    def compile_let(self, expr, environment, let_type):
        validate_let(expr)
        bindings = expr[1]

        # Handle bindings
        match let_type:
            case LET_TYPE.DEFAULT:
                environment = self.create_let_environment(environment, bindings)
            case LET_TYPE.REC:
                environment = self.create_letrec_environment(environment, bindings)
            case LET_TYPE.STAR:
                compiler_error("let* unimplemented.")
            case _:
                compiler_error("unimplemented let type.")
        

        # Compile sub expressions
        sub_expressions = expr[2:]
        self.compile_subexprs(sub_expressions, environment)

        # Tear down locals
        for _ in range(len(bindings)):
            self.code.append(I.SQUASH)

    def update_indices(self, environment, shift) -> dict:
        new_environment = {}
        for key, value in environment.items():
            new_environment[key] = value.copy()
            new_environment[key].shift(shift)
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

    def compile_lambda_body(self, args, body, free_vars, lambda_name=None):
        # Jump with placeholder value
        self.code.append(I.JMP)
        self.code.append(box_fixnum(0))
        function_start = len(self.code)

        # Create theoretical environment to compile lambda within
        lambda_environment = {}
        i = 0
        for x in range(len(free_vars)-1, -1, -1):# Free vars
            variable = free_vars[x]
            lambda_environment[variable] = EnvItem(i)
            i += 1
        for x in range(len(args)-1, -1, -1): # Lambda arguments
            variable = args[x]
            lambda_environment[variable] = EnvItem(i)
            i += 1
        if lambda_name != None:
            lambda_environment[lambda_name] = EnvItem(0, EIT.CLOSURE)

        # Assume lambdas only take 1 expr. Hence, in_tail_pos=True
        self.compile(body, lambda_environment, in_tail_pos=True)

        # Squash free variables and args
        for i in range(len(args) + len(free_vars)):
            self.code.append(I.SQUASH)

        # Return
        self.code.append(I.RETURN)

        # Update placeholder jump
        jump_length = len(self.code) - function_start
        self.code[function_start-1] = box_fixnum(jump_length * OP_LEN)

        # Return the function start
        return function_start

    def compile_lambda(self, expr, environment):
        args = expr[1]
        free_vars = expr[2]
        body = expr[3]

        # Compile the lambda body
        function_start = self.compile_lambda_body(args, body, free_vars)

        # Push the function addr (code index)
        self.code.append(I.LOAD64)
        self.code.append(box_fixnum(function_start * OP_LEN))

        # Construct vector of free args and add n_args
        self.compile_vector(free_vars, self.update_indices(environment, 1))
        self.code.append(I.LOAD64)
        self.code.append(box_fixnum(len(args)))

        # Closure captures n_args, vector of free arguments, and function addr
        self.code.append(I.ALLOC_CLO)

    def compile_rec_lambda(self, expr, lambda_name, environment):
        args = expr[1]
        free_vars = expr[2]
        body = expr[3]

        if lambda_name in free_vars:
            free_vars.remove(lambda_name)

        # Compile the lambda body as normal
        function_start = self.compile_lambda_body(args, body, free_vars, lambda_name)

        # Push the function addr (code index)
        self.code.append(I.LOAD64)
        self.code.append(box_fixnum(function_start * OP_LEN))

        # Compile free_vars (with potential placeholders)
        for i in range(len(free_vars) - 1, -1, -1):
            el = free_vars[i]
            self.compile(el, self.update_indices(environment, len(free_vars) - 1 - i))
        self.code.append(I.ALLOC_VEC)
        self.code.append(box_fixnum(len(free_vars)))

        # Load n_args
        self.code.append(I.LOAD64)
        self.code.append(box_fixnum(len(args)))

        # Closure captures n_args, vector of free arguments, and function addr
        self.code.append(I.ALLOC_CLO)
    
    def general_fn_emit(self, expr, n_args, opcode, environment):
        validate_args(expr, n_args)
        # Compile args
        for i, sub_expr in enumerate(expr[1:]):
            self.compile(sub_expr, self.update_indices(environment, i))
        # Add specific opcode
        self.code.append(opcode)
    
    def compile_subexprs(self, sub_expressions, environment):
        for i, sub_expr in enumerate(sub_expressions):
            self.compile(sub_expr, environment, in_tail_pos= (i == len(sub_expressions)-1))

            # Drop unused values
            if i < len(sub_expressions) - 1:
                self.code.append(I.DROP)
        
    def compile(self, expr, environment, in_tail_pos=False) -> list:
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
            case EmptyList():
                emit(I.LOAD64)
                emit(box_empty_list())
            case list():
                # Empty list
                if len(expr) == 0:
                    compiler_error("invalid syntax: ()")

                # List as a function call (only lambda can do this atm)
                if isinstance(expr[0], list):
                    # Make the function call
                    self.compile_function(expr, environment, in_tail_pos)
                    return
                
                # Function call
                func_name = expr[0]
                if func_name in environment:
                    self.compile_function(expr, environment, in_tail_pos)
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

                    case "eq?":
                        self.general_fn_emit(expr, 2, I.KLEG, environment)

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
                        self.compile(expr[2], environment, in_tail_pos=True)
                        emit(I.JMP)
                        emit(box_fixnum(0))
                        ckpt2 = len(self.code)

                        # -- Else --
                        self.compile(expr[3], environment, in_tail_pos=True)
                        ckpt3 = len(self.code)
                        
                        # Update placeholder values
                        self.code[ckpt1-1] = box_fixnum((ckpt2 - ckpt1) * OP_LEN)
                        self.code[ckpt2-1] = box_fixnum((ckpt3 - ckpt2) * OP_LEN)

                    # n-ary functions
                    case "let":
                        self.compile_let(expr, environment, LET_TYPE.DEFAULT)

                    case "letrec":
                        self.compile_let(expr, environment, LET_TYPE.REC)

                    case "begin":
                        # Compile all subexpressions
                        sub_expressions = expr[1:]
                        self.compile_subexprs(sub_expressions, environment)

                    case "list":
                        # Compile all args to the stack
                        args = expr[1:]
                        for i, sub_expr in enumerate(args):
                            self.compile(sub_expr, self.update_indices(environment, i))
                        # Add the empty list to serve as the end of the list
                        emit(I.LOAD64)
                        emit(box_empty_list())

                        # Cons everything together
                        for _ in range(len(args)):
                            emit(I.CONS)
                    
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

                    # Lambda
                    case "lambda":
                        self.compile_lambda(expr, environment)

                    case _:
                        compiler_error(f"Calling unbound/undefined '{func_name}' as a function.")
                        

            case str():
                # Local variables
                if expr in environment:
                    # Duplicate their value onto the top of the stack\
                    env_item = environment[expr]
                    match env_item.type:
                        case EIT.DEFAULT:
                            emit(I.GET)
                            emit(box_fixnum(env_item.position))
                        case EIT.CLOSURE:
                            emit(I.GET_CLOSURE)
                        case EIT.FREE_VAR:
                            compiler_error("Free Vars references in environment currently unimplemented.")
                else:
                    compiler_error(f"Use of undefined variable '{expr}'")
    
    def compile_function(self, expr, environment, in_tail_pos):
        args = expr[1:]
        # Add space for ret and closure
        if not in_tail_pos:
            # Make space for return, rdi, and rbp
            num_replacements = 3
            for i in range(num_replacements):
                self.code.append(I.PUSH_UNSPEC)
            environment = self.update_indices(environment, num_replacements)

        # Compile args
        for i, arg in enumerate(args):
            self.compile(arg, self.update_indices(environment, i))

        # Load lambda or function call
        self.compile(expr[0], self.update_indices(environment, len(args)))

        # Load the # of args onto the stack
        self.code.append(I.LOAD64)
        self.code.append(box_fixnum(len(args)))

        # Make the call
        if in_tail_pos:
            self.code.append(I.TAILCALL)
        else:
            self.code.append(I.FUNCALL)

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

def lift_lambdas(expr, bound: set, free: set):
    match expr:
        case int() | Character() | String() | EmptyList():
            return
        case str() if expr in bound or expr in BUILTINS:
            return
        case str():
            free.add(expr)
            return
        case list():
            # Empty list
            if len(expr) == 0:
                return
            
            # Function call
            match expr[0]:
                case "lambda":
                    validate_args(expr, 2)
                    local_bound = set()
                    local_free = set()
                    
                    # Bind lambda args
                    for variable in expr[1]:
                        if not isinstance(variable, str):
                            compiler_error(f"Non-str variable in lambda: {variable}")
                        local_bound.add(variable)

                    # Recurse
                    lift_lambdas(expr[2], local_bound, local_free)
                    
                    # Add all truly free variables to the structure
                    free_vars = []
                    for variable in local_free:
                        if variable not in local_bound:
                            free_vars.append(variable)

                        # Propagate free vars up
                        if variable not in bound:
                            free.add(variable)

                    # Sort for determinism
                    free_vars.sort()
                    expr.insert(2, free_vars)
                case "let":
                    # Validate the let and add the bindings to the bound set
                    let_bindings = validate_let(expr)
                    sub_bound = bound.union(let_bindings)
                    
                    # Lift lambdas in let bindings
                    for pair in expr[1]:
                        lift_lambdas(pair[1], bound, free)

                    # Recurse over let statements
                    for sub_expr in expr[2:]:
                        lift_lambdas(sub_expr, sub_bound, free)
                case "letrec":
                    # Validate the letrec and add bindings to the bound set
                    let_bindings = validate_let(expr)
                    sub_bound = bound.union(let_bindings)

                    # Lift lambdas in bindings, considering name to be bound
                    for pair in expr[1]:
                        lift_lambdas(pair[1], sub_bound, free)
                    
                    # Recurse over let statements
                    for sub_expr in expr[2:]:
                        lift_lambdas(sub_expr, sub_bound, free)

                case _:
                    for sub_expr in expr:
                        lift_lambdas(sub_expr, bound, free)
        case _:
            raise NotImplementedError(expr)
                    

def compile_program():
    # Parse the Scheme file (from stdin)
    source = sys.stdin.read()
    program = scheme_parse(source)

    # Compile all functions at the root of the file
    compiler = Compiler()
    for i, function in enumerate(program):
        lift_lambdas(function, set(), set())
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