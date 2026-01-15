import sys
from compiler import Compiler
from parser import scheme_parse

def compile_program():
    source = sys.stdin.read()
    program = scheme_parse(source)
    compiler = Compiler()
    compiler.compile_function(program)
    compiler.write_to_stream(sys.stdout.buffer)

if __name__ == "__main__":
    compile_program()