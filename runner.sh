#!/bin/bash

# Check number of args for usage
if [[ $# -ne 1 ]]; then
    echo "Usage: ./runner.sh scheme_file_name.scm"
    exit -1
fi

echo "[RUNNER] Compiling '$1' to bytecode..."
python3 compiler.py < $1 > compiled.bc

if [[ $? -ne 0 ]]; then
    echo "[RUNNER] Compilation failed."
    exit -2
fi

echo "[RUNNER] Done."
echo "[RUNNER] Invoking interpreter to run compiled bytecode."
echo
./interpreter < compiled.bc
echo
echo "[RUNNER] Done."

exit 0