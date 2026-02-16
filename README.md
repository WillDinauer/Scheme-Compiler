# Scheme-Compiler

## Requirements

- Python 3.10+ (for parser and compiler)
- GCC 12+ with C++20 support (for building the interpreter)

## Building

The interpreter must be compiled. To build this interpreter, run `make`. To build the interpreter with debug information, run `make debug`. (Note: debug information must be disabled to run the tests). For a fresh build, run `make clean` beforehand.

## Usage

For a particular scheme file:
```
./runner.sh scheme_file_name.sh
```
For example,
```
./runner.sh test.scm
```
This script will parse and compile the Scheme file into `compiled.bc`, which is passed to the interpreter for running.

## Testing

To run all the tests, run:
```
./runner.sh tests
```
This will test that every scheme file in the `tests/` directory builds AND produces expected ouput. There are both good and bad tests, each in their own repositories (`tests/good` and `tests/bad`).

## Parser and Compiler

The parser/compiler produces human-readable bytecode, and saves it to `code.txt` upon completion. It expects to receive a text file of Scheme code (.scm). To run the parser and compiler independently, you can run something like:
```
python3 compiler.py < test.scm > test.bc
```
The file `test.bc` then contains the bytecode (which can be run by the interpreter).

## Interpreter

To build the interpreter, run `make`. Running `make clean` will allow for a fresh build of the interpreter.

The interpreter expects custom bytecode from stdin, as produced by the compiler. It can be run independently such as:
```
./interpreter test.bc
```
The result is printed to stdout by default.