#!/bin/bash

COMPILED_FILE=compiled.bc
# Colors
RED="\033[0;31m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
NC="\033[0m"

# Check number of args for usage
if [[ $# -ne 1 ]]; then
    echo "Usage: ./runner.sh scheme_file.scm"
    exit -1
fi

compile() {
    python3 compiler.py < $1 > $2
}

# -- Run all the tests --
if [[ "$1" == "tests" ]]; then
    # Build the interpreter
    echo -e "${BLUE} -- BUILDING INTERPRETER -- ${NC}"
    make clean && make
    echo -e "${GREEN} -- BUILD SUCCEEDED -- ${NC}"
    echo

    # Run good tests
    TEMP=tests/temp.txt
    GOOD_DIR=tests/good
    BAD_DIR=tests/bad
    echo -e "${BLUE} -- RUNNING GOOD TESTS -- ${NC}"
    for TEST in `ls $GOOD_DIR | sort -g`; do
        test_dir=$GOOD_DIR/$TEST
        if [ -d "$test_dir" ]; then
            echo -n "Running good test $TEST..."
            compile "$test_dir/test.scm" "tests/$COMPILED_FILE"

            if [[ $? -ne 0 ]]; then
                rm "tests/$COMPILED_FILE"
                echo "Compilation failed for test $TEST"
                exit -1
            fi
            
            # Run interpreter
            ./interpreter < "tests/$COMPILED_FILE" > "$TEMP"
            if cmp -s $TEMP $test_dir/expected.txt; then
                echo -e "${GREEN}PASSED.${NC}"
            else
                echo -e "${RED}FAILED.${NC}"
                echo "Running diff to compare."
                diff $TEMP $test_dir/expected.txt
                rm "tests/$COMPILED_FILE"
                rm $TEMP
                exit -1
            fi

            # Clean up
            rm "tests/$COMPILED_FILE"
            rm $TEMP
        fi
    done
    echo -e "${GREEN} -- PASSED ALL GOOD TESTS -- ${NC}"
    echo

    # Run bad tests
    echo -e "${BLUE} -- RUNNING ALL BAD TESTS -- ${NC}"
    for TEST in `ls $BAD_DIR | sort -g`; do
        test_dir=$BAD_DIR/$TEST
        if [ -d "$test_dir" ]; then
            echo -n "Running bad test $TEST..."
            python3 compiler.py < "$test_dir/test.scm" 2> $TEMP
            if [[ $? == 0 ]]; then
                echo -e "${RED}FAILED.${NC} (these tests should not compile...)"
                exit -1
            fi

            tail -n 1 $TEMP > tests/out.txt
            rm $TEMP
            if cmp -s tests/out.txt $test_dir/expected.txt; then
                echo -e "${GREEN}PASSED.${NC}"
            else
                echo -e "${RED}FAILED.${NC}"
                echo "Running diff to compare."
                diff tests/out.txt $test_dir/expected.txt
                rm tests/out.txt
                exit -1
            fi
            rm tests/out.txt
        fi
    done
    echo -e "${GREEN} -- PASSED ALL BAD TESTS -- ${NC}"
    echo
    
    echo -e "${GREEN}Passed ALL tests! (good and bad!)${NC}"
    exit 0
fi


# -- Run a specific test -- 
echo "[RUNNER] Compiling '$1' to bytecode..."
compile $1 $COMPILED_FILE

if [[ $? -ne 0 ]]; then
    echo "[RUNNER] Compilation failed."
    exit -1
fi

echo "[RUNNER] Done."
echo "[RUNNER] Invoking interpreter to run compiled bytecode."
echo
./interpreter < $COMPILED_FILE
echo
echo "[RUNNER] Done."

exit 0