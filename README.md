# Scheme-Compiler

## Usage
```
./runner.sh scheme_file_name.sh
```
For example,
```
./runner.sh test.scm
```
This script will parse and compile the Scheme file into `compiled.bc`, which is passed to the interpreter for running.

## Parser and Compiler

The parser/compiler produces human-readable bytecode, and saves it to `code.txt` upon completion. It expects to receive a text file of Scheme code (.scm). To run the parser and compiler independently, you can run something like:
```
python3 compiler.py < test.scm > test.bc
```
The file `test.bc` then contains the bytecode (which can be run by the interpreter).

## Interpreter

The interpreter expects custom bytecode from stdin, as produced by the compiler. To enable debugging in the interpreter, uncomment the `#define DEBUG_ACTIVE` line for some tracing. It can be run independently such as:
```
./interpreter test.bc
```
The result is printed to stdout by default (although this is not standard behavior in Scheme, but is useful for now).