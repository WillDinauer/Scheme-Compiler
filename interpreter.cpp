#include <iostream>
#include <unistd.h>
#include <vector>
#include <memory>
#include <variant>
#include <stdexcept>
#include <format>
#include <iomanip>
#include "interpreter.h"

// Heap
uint64_t heap[1024];
uint64_t* heap_ptr = heap;
uint64_t* heap_end = heap_ptr + 1024;

int64_t create_fixnum_ptr(int64_t num) {
    return (num << FIXNUM_SHIFT) | FIXNUM_TAG;
}

uint64_t create_char_ptr(char c) {
    return ((uint64_t) c << CHAR_SHIFT) | CHAR_TAG;
}

std::string type_to_string(VT type) {
    switch (type) {
        case VT::FIXNUM:
            return "FIXNUM";
        case VT::CHAR:
            return "CHAR";
        case VT::BOOL:
            return "BOOL";
        case VT::EMPTY_LIST:
            return "NIL";
        case VT::PAIR:
            return "CONS";
        case VT::STRING:
            return "STRING";
        case VT::VECTOR:
            return "VECTOR";
        case VT::SYMBOL:
            return "SYMBOL";
        case VT::CLOSURE:
            return "CLOSURE";
        case VT::UNSPECIFIED:
            return "UNSPECIFIED";
        case VT::UNKNOWN:
            return "UNKNOWN";
    }
}

// Figure out the type based on the tag information
VT resolve_type(uint64_t value) {
    if ((value & FIXNUM_MASK) == FIXNUM_TAG) {
        return VT::FIXNUM;
    }
    if ((value & CHAR_MASK) == CHAR_TAG) {
        return VT::CHAR;
    }
    if ((value & BOOL_MASK) == BOOL_TAG) {
        return VT::BOOL;
    }
    if ((value & EL_MASK) == EL_TAG) {
        return VT::EMPTY_LIST;
    }
    switch (value & PTR_MASK) {
        case PAIR_TAG:
            return VT::PAIR;
        case VECTOR_TAG:
            return VT::VECTOR;
        case STRING_TAG:
            return VT::STRING;
        case SYMBOL_TAG:
            return VT::SYMBOL;
        case CLOSURE_TAG:
            return VT::CLOSURE;
    }
    if ((int64_t) value == UNSPEC_VAL) {
        return VT::UNSPECIFIED;
    }
    throw std::runtime_error(std::format("Unable to resolve type for value: {}", value));
}

// Zero out tag for a given pointer
void strip_tag(uint64_t& value) {
    uint64_t nuker;     // Nuke the tag
    switch (resolve_type(value)) {
        case VT::FIXNUM:
        {
            nuker = FIXNUM_NUKE;
            break;
        }
        case VT::BOOL:
        {
            nuker = BOOL_NUKE;
            break;
        }
        case VT::CHAR:
        {
            nuker = CHAR_NUKE;
            break;
        }
        case VT::PAIR:
        case VT::VECTOR:
        case VT::STRING:
        case VT::SYMBOL:
        case VT::CLOSURE:
        {
            nuker = PTR_NUKE;
            break;
        }
        default:
        {
            throw std::runtime_error("trying to strip unstrippable obj");
        }
    }
    // Zero out tag bits
    value &= nuker;
}

// Check if value matches expected type. Throw an error if not
void type_check_or_fail(uint64_t value, VT desired_type) {
    VT type = resolve_type(value);
    if (type != desired_type) {
        std::string expected = type_to_string(desired_type);
        std::string got = type_to_string(type);
        throw std::runtime_error(std::format("Type check failed (Expected: '{}' Got: '{}')", expected, got));
    }
}

// Convert uint64_t representation of boolean to c++ true/false
bool resolve_bool(uint64_t value) {
    type_check_or_fail(value, VT::BOOL);
    return (value >> BOOL_SHIFT) == T_BOOL_VAL;
}

char resolve_char(uint64_t value) {
    type_check_or_fail(value, VT::CHAR);
    return static_cast<char>(value >> CHAR_SHIFT);
}

// Get the value by shifting right the appropriate amount
int64_t resolve_fixnum(int64_t value) {
    type_check_or_fail(value, VT::FIXNUM);
    return value >> FIXNUM_SHIFT;
}

std::string resolve_string(uint64_t value) {
    type_check_or_fail(value, VT::STRING);
    strip_tag(value);
    uint64_t* ptr = (uint64_t *) value;

    // Read length
    int64_t length = resolve_fixnum(*ptr);
    ptr += WORD_LEN;

    // Read characters
    char* char_ptr = (char *) ptr;
    std::string res;
    for (int64_t i = 0; i < length; i++) {
        res += *(char_ptr++);
    }
    return res;
}

std::string cons_to_string(uint64_t value) {
    type_check_or_fail(value, VT::PAIR);
    strip_tag(value);
    uint64_t* cons_ptr = (uint64_t *) value;

    uint64_t first = *cons_ptr;
    cons_ptr += WORD_LEN;
    uint64_t second = *cons_ptr;
    return "(" + value_to_string(first) + " " + value_to_string(second) + ")";
}

std::string vector_to_string(uint64_t value) {
    // Get ptr to vector
    type_check_or_fail(value, VT::VECTOR);
    strip_tag(value);
    uint64_t* vec_ptr = (uint64_t *) value;

    // Get vector length
    int64_t length = resolve_fixnum(*vec_ptr);
    vec_ptr += WORD_LEN;

    // Recurse over vector elements
    std::string res = "#(";
    for (int64_t i = 0; i < length; i++) {
        // Spaces between elements
        if (i != 0) {
            res += " ";
        }
        res += value_to_string(*vec_ptr);
        vec_ptr += WORD_LEN;
    }
    res += ")";
    return res;
}

// Convert a closure to a string for printing/debugging
std::string closure_to_string(uint64_t value) {
    type_check_or_fail(value, VT::CLOSURE);
    strip_tag(value);
    uint64_t* ptr = (uint64_t *) value;

    // Capture args, vector, return
    std::string res = "[";
    int64_t n_args = resolve_fixnum(*ptr);
    res += std::to_string(n_args) + "a, ret: ";
    ptr += WORD_LEN * 2;
    res += std::to_string(resolve_fixnum(*ptr)) + "]";
    return res;
}

// Convert true/false to #t or #f, respectively
std::string cpp_bool_to_scheme_bool(bool value) {
    return value ? "#t" : "#f";
}

// Convert value to [VALUE - resolved_value] pair
std::string value_to_string(uint64_t value, bool include_type) {
    VT type = resolve_type(value);
    std::string res = "[" + type_to_string(type);

    std::string v_string;
    bool default_case = false;
    switch (type) {
        case VT::FIXNUM:
            v_string = std::to_string(resolve_fixnum(value));
            break;
        case VT::CHAR:
            v_string = "#\\";
            v_string += resolve_char(value);
            break;
        case VT::BOOL:
            v_string = cpp_bool_to_scheme_bool(resolve_bool((value)));
            break;
        case VT::STRING:
            v_string = resolve_string(value);
            break;
        default:
            default_case = true;
            v_string = "";
    }
    // Value only
    if (!include_type) {
        return v_string;
    }

    // Extra chars for nice printing
    if (!default_case) {
        v_string = ": " + v_string;
    }

    res += v_string + "]";
    return res;
}

// Read a qword from the code
uint64_t read_word(size_t& pc, std::vector<uint8_t>& code) {
    int bits_per_byte = 8;
    uint64_t ret = 0;

    // Read in bytes 1 at a time, little-endian
    for (int i = 0; i < WORD_LEN; i++) {
        uint64_t b = (uint64_t)code[pc] << (i * bits_per_byte);
        ret |= b;
        pc++;
    }

    return ret;
}

// Read a word from the code and check its type
uint64_t typed_read_word(size_t& pc, std::vector<uint8_t>& code, VT type) {
    uint64_t value = read_word(pc, code);
    type_check_or_fail(value, type);
    return value;
}

void validate_allocation(uint64_t size) {
    if (heap_ptr + size > heap_end) {
        throw std::runtime_error("Ran out of heap space.");
    }
}

// Write a word to the heap
void heap_write_word(uint64_t value) {
    validate_allocation(WORD_LEN);
    *heap_ptr = value;
    heap_ptr += WORD_LEN;
}

// Align the heap for future allocations
void align_heap() {
    heap_ptr += (WORD_LEN - 1);
    heap_ptr = (uint64_t *) ((uint64_t) heap_ptr & PTR_NUKE);
}

char *get_char_ptr(uint64_t idx_value, uint64_t str_value) {
    strip_tag(str_value);
    uint64_t* str_ptr = (uint64_t *) str_value;

    // Get length and index
    uint64_t length_value = *str_ptr;
    int64_t length = resolve_fixnum(length_value);
    int64_t idx = resolve_fixnum(idx_value);
    if (idx >= length || idx < 0) {
        throw std::runtime_error(std::format("Invalid string index: (index {} for length of {})", idx, length));
    }

    // Resolve the char_ptr
    str_ptr += WORD_LEN;
    char *c_ptr = (char *) str_ptr;
    c_ptr += idx;
    return c_ptr;
}

uint64_t *get_vector_ptr(uint64_t idx_ptr, uint64_t vec_ptr) {
        // Resolve to their true values
        strip_tag(vec_ptr);
        int64_t idx = resolve_fixnum(idx_ptr);
        uint64_t *vec_slot = (uint64_t *) vec_ptr;
        int64_t length = resolve_fixnum(*vec_slot);
        if (idx >= length || idx < 0) {
            throw std::runtime_error(std::format("Invalid vector index {} for length {}", idx, length));
        }

        // Index into the vector
        vec_slot += (WORD_LEN * (1 + idx));
        return vec_slot;
}

uint64_t *get_closure_ptr(uint64_t idx_ptr, uint64_t closure_ptr) {
    // Resolve to true values
    strip_tag(closure_ptr);
    uint64_t idx = resolve_fixnum(idx_ptr);
    if (idx >= CLOSURE_LEN || idx < 0) {
        throw std::runtime_error(std::format("Invalid closure index {} for length {}", idx, CLOSURE_LEN));
    }
    
    uint64_t *clo_slot = (uint64_t *) closure_ptr;
    clo_slot += (WORD_LEN * idx);
    return clo_slot;
}

void validate_num_args(uint64_t* closure, int64_t num_args) {
    // Validate # of arguments
    int64_t check_ct = resolve_fixnum(*closure);
    if (num_args != check_ct) {
        throw std::runtime_error(std::format("Invalid number of arguments passed to lambda expr...({} for {} expected)", num_args, check_ct));
    }
}

// Get length of free variable vector, given a closure
int64_t get_fv_length(uint64_t *closure) {
    closure += WORD_LEN;
    uint64_t vec_ptr = *closure;
    type_check_or_fail(vec_ptr, VT::VECTOR);
    strip_tag(vec_ptr);
    uint64_t* vector = (uint64_t *) vec_ptr;

    return resolve_fixnum(*vector);
}

// Push the free variables, and return the length of the FV vector
void push_free_variables(uint64_t *closure) {
    // Resolve vector
    closure += WORD_LEN;
    uint64_t vec_ptr = *closure;
    type_check_or_fail(vec_ptr, VT::VECTOR);
    strip_tag(vec_ptr);
    uint64_t* vector = (uint64_t *) vec_ptr;

    // Push free variable values to the stack
    int64_t length = resolve_fixnum(*vector);
    for (int64_t i = 0; i < length; i++) {
        vector += WORD_LEN;
        stk.push(*vector);
    }
}

// Remove previous locals (for tailcall optimization)
void teardown(uint64_t *closure) {
    // Copy all arguments to right above the return
    int64_t num_args = resolve_fixnum(*closure);
    for (int64_t i = 0; i < num_args; i++) {
        int64_t src = stk.size() - num_args + i;
        int64_t dst = rbp + i;
        stk.overwrite_from_base(src, dst);
    }

    // Pop unneeded args
    while (stk.size() > rbp + num_args) {
        stk.pop();
    }
}

// Run the code
std::unique_ptr<uint64_t> interpret(std::vector<uint8_t>& code) {
    size_t pc = 0;
    rdi = 0;
    rbp = 0;

    while (pc < code.size()) {
        DEBUG_MSG(std::format("\npc: {}", pc));
        #ifdef DEBUG
            stk.print_state();
        #endif
        // truncate instr to lowest byte
        uint8_t instr = read_word(pc, code);
        switch(instr) {
            case opcode_t::LOAD64:
            {
                DEBUG_MSG("LOAD64");
                uint64_t value = read_word(pc, code);
                stk.push(value);
                break;
            }
            case opcode_t::ADD1:
            {
                DEBUG_MSG("ADD1");
                int64_t value = stk.pop_and_check_type(VT::FIXNUM);

                value += (1 << FIXNUM_SHIFT);
                stk.push(value);
                break;
            }
            case opcode_t::SUB1:
            {
                DEBUG_MSG("SUB1");
                int64_t value = stk.pop_and_check_type(VT::FIXNUM);

                value -= (1 << FIXNUM_SHIFT);
                stk.push(value);
                break;
            }
            case opcode_t::INT_TO_CHAR:
            {
                DEBUG_MSG("INT_TO_CHAR");
                int64_t value = stk.pop_and_check_type(VT::FIXNUM);

                value = value >> FIXNUM_SHIFT;  // Remove fixnum tag
                value = value << CHAR_SHIFT;    // Make space for char tag
                value |= CHAR_TAG;              // Add char tag
                stk.push(value);
                break;
            }
            case opcode_t::CHAR_TO_INT:
            {
                DEBUG_MSG("CHAR_TO_INT");
                uint64_t value = stk.pop_and_check_type(VT::CHAR);

                value = value >> CHAR_SHIFT;                // Remove char tag
                value = (int64_t) value << FIXNUM_SHIFT;    // Make space for fixnum tag
                value |= FIXNUM_TAG;                        // Add fixnum tag
                stk.push(value);
                break;
            }
            case opcode_t::NULL_CHECK:
            {
                DEBUG_MSG("NULL_CHECK");
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                type == VT::EMPTY_LIST ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::ZERO_CHECK:
            {
                DEBUG_MSG("ZERO_CHECK");
                uint64_t value = stk.pop_and_check_type(VT::FIXNUM);

                uint64_t zero = FIXNUM_TAG;
                value == zero ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::INT_CHECK:
            {
                DEBUG_MSG("INT_CHECK");
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                type == VT::FIXNUM ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::BOOL_CHECK:
            {
                DEBUG_MSG("BOOL_CHECK");
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                type == VT::BOOL ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::NOT:
            {
                DEBUG_MSG("NOT");
                uint64_t value = stk.pop_and_check_type(VT::BOOL);

                resolve_bool(value) ? stk.push(FALSE_BOOL) : stk.push(TRUE_BOOL);
                break;
            }
            case opcode_t::ADD:
            {
                DEBUG_MSG("ADD");
                uint64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t v2 = stk.pop_and_check_type(VT::FIXNUM);

                // Remove tags
                strip_tag(v1);
                strip_tag(v2);

                // Add and push
                v2 += v1;
                v2 |= FIXNUM_TAG;
                stk.push(v2);
                break;
            }
            case opcode_t::SUB:
            {
                DEBUG_MSG("SUB");
                uint64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t v2 = stk.pop_and_check_type(VT::FIXNUM);

                // Remove tag
                strip_tag(v1);
                strip_tag(v2);

                // Sub and push
                v2 -= v1;
                v2 |= FIXNUM_TAG;
                stk.push(v2);
                break;
            }
            case opcode_t::MUL:
            {
                DEBUG_MSG("MUL");
                int64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                int64_t v2 = stk.pop_and_check_type(VT::FIXNUM);

                // Get actual values
                v1 = resolve_fixnum(v1);
                v2 = resolve_fixnum(v2);
                
                // Multiply and push
                v1 *= v2;
                stk.push(create_fixnum_ptr(v1));
                break;
            }
            case opcode_t::LT:
            {
                DEBUG_MSG("LT");
                int64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                int64_t v2 = stk.pop_and_check_type(VT::FIXNUM);
                
                v2 < v1 ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::EQL:
            {
                DEBUG_MSG("EQL");
                uint64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t v2 = stk.pop_and_check_type(VT::FIXNUM);

                v2 == v1 ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::KLEG: // Kompare Literal Eguals
            {
                DEBUG_MSG("KLEG");
                uint64_t v1 = stk.pop();
                uint64_t v2 = stk.pop();

                v2 == v1 ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::GET:
            {
                DEBUG_MSG("GET");
                uint64_t value = read_word(pc, code);

                // Value becomes an index to reach into on the stack
                value = resolve_fixnum(value);
                #ifdef DEBUG
                    std::cout << "Get Index: " << value << std::endl;
                #endif

                // Reach down into stack and duplicate value at index onto top
                value = stk.get_value_from_top(value);
                stk.push(value);
                break;
            }
            case opcode_t::DROP:
            {
                DEBUG_MSG("DROP");
                // Pop and drop the value on the ground
                stk.pop();
                break;
            }
            case opcode_t::SQUASH:
            {
                DEBUG_MSG("SQUASH");
                uint64_t value = stk.pop();
                stk.pop();
                stk.push(value);
                break;
            }
            case opcode_t::JMP:
            {
                DEBUG_MSG("JMP");
                uint64_t jump_ptr = typed_read_word(pc, code, VT::FIXNUM);
                int64_t jump_length = resolve_fixnum(jump_ptr);
                DEBUG_MSG(jump_length);
                pc += jump_length;
                break;
            }
            case opcode_t::JIF:
            {
                DEBUG_MSG("JIF");
                uint64_t jump_length = typed_read_word(pc, code, VT::FIXNUM);
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                if (type == VT::BOOL && !resolve_bool(value)) {
                    DEBUG_MSG("JUMP IN JIF...(condition == '#f')");
                    pc += resolve_fixnum(jump_length);
                }
                break;
            }
            case opcode_t::CONS:
            {
                DEBUG_MSG("CONS");
                validate_allocation(2*WORD_LEN);

                // Grab CAR and CDR
                uint64_t cdr = stk.pop();
                uint64_t car = stk.pop();
                
                // Address to put on stack
                uint64_t addr = (uint64_t) heap_ptr | PAIR_TAG;

                // Place onto heap, then push addr
                heap_write_word(car);
                heap_write_word(cdr);
                stk.push(addr);
                break;
            }
            case opcode_t::CAR:
            {
                DEBUG_MSG("CAR");
                uint64_t tagged_ptr = stk.pop_and_check_type(VT::PAIR);
                strip_tag(tagged_ptr);
                // Get addr of CAR and dereference
                uint64_t* addr = (uint64_t*) tagged_ptr;
                uint64_t value = *addr;
                stk.push(value);
                break;
            }
            case opcode_t::CDR:
            {
                DEBUG_MSG("CDR");
                uint64_t tagged_ptr = stk.pop_and_check_type(VT::PAIR);
                strip_tag(tagged_ptr);
                // Get addr of CDR and dereference
                uint64_t* addr = (uint64_t*) tagged_ptr + WORD_LEN;
                stk.push(*addr);
                break;
            }
            case opcode_t::ALLOC_STR:
            {
                DEBUG_MSG("ALLOC_STR");
                uint64_t value = typed_read_word(pc, code, VT::FIXNUM);
                int64_t length = resolve_fixnum(value);

                if (length < 0) {
                    throw std::runtime_error(std::format("Call to allocate string with negative length value: {}", length));
                }

                // allocation for length (8 bytes) and chars ('length' bytes)
                validate_allocation(length + WORD_LEN);

                // Save the current location of the heap ptr as the value to push
                uint64_t ptr = (uint64_t) heap_ptr | STRING_TAG;

                // Write length to the heap
                heap_write_word(value);
                
                // Read 'length' # of chars and place them on the heap
                char* char_ptr = (char *) heap_ptr;
                for (int i = 0; i < length; i++) {
                    uint64_t char_value = stk.pop_and_check_type(VT::CHAR);
                    char c = resolve_char(char_value);
                    *char_ptr = c;
                    char_ptr++;
                }

                // Align the heap ptr
                heap_ptr += length;
                align_heap();

                stk.push(ptr);
                break;
            }
            case opcode_t::STR_REF:
            {
                DEBUG_MSG("STR_REF");
                // Index to grab
                uint64_t idx_value = stk.pop_and_check_type(VT::FIXNUM);

                // Get string pointer
                uint64_t str_value = stk.pop_and_check_type(VT::STRING);

                // Resolve the ptr into the string
                char* c_ptr = get_char_ptr(idx_value, str_value);
                char c = *c_ptr;
                uint64_t char_ptr = create_char_ptr(c);
                stk.push(char_ptr);
                break;
            }
            case opcode_t::STR_SET:
            {
                DEBUG_MSG("STR_SET");
                // Char to set
                uint64_t char_value = stk.pop_and_check_type(VT::CHAR);
                char c = resolve_char(char_value);

                // Get index and string
                uint64_t idx_value = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t str_value = stk.pop_and_check_type(VT::STRING);

                // Ptr to specific char in string
                char* c_ptr = get_char_ptr(idx_value, str_value);

                // Set the char
                *c_ptr = c;
                stk.push(UNSPEC_VAL);
                break;
            }
            case opcode_t::STR_APPEND:
            {
                DEBUG_MSG("STR_APPEND");
                uint64_t value = typed_read_word(pc, code, VT::FIXNUM);
                int64_t num_strs = resolve_fixnum(value);
                if (num_strs < 0) { 
                    throw std::runtime_error(std::format("Invalid # of strings for call to str_append: {}", num_strs));
                }

                uint64_t* new_str_ptr = heap_ptr;
                heap_ptr += WORD_LEN;

                int64_t total_length = 0;
                for (int64_t i = 0; i < num_strs; i++) {
                    // Get str from the tag
                    uint64_t str_value = stk.pop_and_check_type(VT::STRING);
                    strip_tag(str_value);
                    uint64_t* str_ptr = (uint64_t *) str_value;

                    // Validate length
                    uint64_t length_ptr = *str_ptr;
                    int64_t length = resolve_fixnum(length_ptr);
                    validate_allocation(*str_ptr);
                    total_length += length;
                    *new_str_ptr = total_length;

                    // Write characters
                    str_ptr += WORD_LEN;
                    char *heap_p = (char *)heap_ptr;
                    char *c_ptr = (char *)str_ptr;
                    for (int64_t j = 0; j < length; j++) {
                        *heap_p = *c_ptr;
                        heap_p++;
                        c_ptr++;
                    }
                    heap_ptr = (uint64_t *) heap_p;
                }
                align_heap();
                
                // Write length to heap
                uint64_t length_ptr = create_fixnum_ptr(total_length);
                *new_str_ptr = length_ptr;
                uint64_t ptr = (uint64_t) new_str_ptr | STRING_TAG;

                // Push ptr to the newly created string
                stk.push(ptr);
                break;
            }
            case opcode_t::ALLOC_VEC:
            {
                DEBUG_MSG("ALLOC_VEC");
                uint64_t length_ptr = typed_read_word(pc, code, VT::FIXNUM);
                int64_t length = resolve_fixnum(length_ptr);
                if (length < 0) {
                    throw std::runtime_error(std::format("Invalid length for call to vector allocation: {}", length));
                }

                // Save a ptr to the current spot on the heap and write the vec length
                uint64_t ptr = (uint64_t) heap_ptr | VECTOR_TAG;
                heap_write_word(length_ptr);

                // Write vector args to the heap
                for (int64_t i = 0; i < length; i++) {
                    uint64_t value = stk.pop();
                    heap_write_word(value);
                }

                // Push ptr to vector
                stk.push(ptr);
                break;
            }
            case opcode_t::VEC_REF:
            {
                DEBUG_MSG("VEC_REF");
                // Get vector and index to grab
                uint64_t idx_ptr = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t vec_ptr = stk.pop_and_check_type(VT::VECTOR);

                // Get the object at the index and push it
                uint64_t *vector_slot = get_vector_ptr(idx_ptr, vec_ptr);
                uint64_t result = *vector_slot;
                stk.push(result);
                break;
            }
            case opcode_t::VEC_SET:
            {
                DEBUG_MSG("VEC_SET");
                // Get function args
                uint64_t obj_ptr = stk.pop();
                uint64_t idx_ptr = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t vec_ptr = stk.pop_and_check_type(VT::VECTOR);

                // Swap the object at the index
                uint64_t *vector_slot = get_vector_ptr(idx_ptr, vec_ptr);
                *vector_slot = obj_ptr;

                // Push unspecified
                stk.push(UNSPEC_VAL);
                break;
            }
            case opcode_t::VEC_APPEND:
            {
                DEBUG_MSG("VEC_APPEND");
                uint64_t n_vecs_ptr = typed_read_word(pc, code, VT::FIXNUM);
                int64_t n_vecs = resolve_fixnum(n_vecs_ptr);
                if (n_vecs < 0) {
                    throw std::runtime_error(std::format("Invalid length for call to append vectors: {}", n_vecs));
                }

                uint64_t result = (uint64_t) heap_ptr | VECTOR_TAG;
                uint64_t *new_vec_ptr = heap_ptr;
                heap_ptr += WORD_LEN;
                
                // Iterate over all vector arguments
                int64_t total_length = 0;
                for (int64_t i = 0; i < n_vecs; i++) {
                    // Get next vector
                    uint64_t vec_ptr = stk.pop_and_check_type(VT::VECTOR);
                    strip_tag(vec_ptr);
                    uint64_t *curr_ptr = (uint64_t *) vec_ptr;

                    // Grab vector length and validate
                    uint64_t curr_length_ptr = *curr_ptr;
                    int64_t curr_length = resolve_fixnum(curr_length_ptr);
                    validate_allocation(curr_length);
                    total_length += curr_length;

                    // Write vector elements to new vector
                    curr_ptr += WORD_LEN;
                    for (int64_t j = 0; j < curr_length; j++) {
                        heap_write_word(*curr_ptr);
                    }
                }
                
                // Write total length to heap and push the vector
                uint64_t total_length_ptr = create_fixnum_ptr(total_length);
                *new_vec_ptr = total_length_ptr;
                stk.push(result);
                break;
            }
            case opcode_t::ALLOC_CLO:
            {
                DEBUG_MSG("ALLOC_CLO");
                // # args and vector passed via stack
                uint64_t args_ptr = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t vec_ptr = stk.pop_and_check_type(VT::VECTOR);
                uint64_t addr_ptr = stk.pop_and_check_type(VT::FIXNUM);
                
                // Closure reference
                uint64_t result = (uint64_t) heap_ptr | CLOSURE_TAG;
                
                // Write the # of args and the vector ref to the heap
                heap_write_word(args_ptr);
                heap_write_word(vec_ptr);
                heap_write_word(addr_ptr);

                // Push the addr of the closure
                stk.push(result);
                break;
            }
            case opcode_t::GET_CLOSURE:
            {
                DEBUG_MSG("GET_CLOSURE");
                type_check_or_fail(rdi, VT::CLOSURE);
                stk.push(rdi);
                break;
            }
            case opcode_t::FUNCALL:
            {
                DEBUG_MSG("FUNCALL");
                // Get the arg count immediate
                uint64_t tagged_arg_ct = stk.pop_and_check_type(VT::FIXNUM);
                int64_t num_args = resolve_fixnum(tagged_arg_ct);

                // Get the closure
                uint64_t tagged_closure = stk.pop_and_check_type(VT::CLOSURE);
                strip_tag(tagged_closure);
                uint64_t* closure = (uint64_t*) tagged_closure;

                // Validate arguments
                validate_num_args(closure, num_args);
                push_free_variables(closure);
                int64_t length = get_fv_length(closure);

                // Save registers into the stack
                int64_t empty_slots_idx = length + num_args;
                stk.replace(rdi, empty_slots_idx + 1);
                stk.replace(rbp, empty_slots_idx + 2);

                // Place the current closure in rdi
                tagged_closure = tagged_closure | CLOSURE_TAG;
                rdi = tagged_closure;

                // Update stack base
                rbp = stk.size() - empty_slots_idx;

                // Place the PC into the stack
                stk.replace(create_fixnum_ptr(pc), empty_slots_idx);

                // Jump the PC to the function start
                closure += (2 * WORD_LEN);
                int64_t pc_index = resolve_fixnum(*closure);
                pc = pc_index;
                break;
            }
            case opcode_t::TAILCALL:
            {
                DEBUG_MSG("TAILCALL");
                // Get the arg count immediate
                uint64_t tagged_arg_ct = stk.pop_and_check_type(VT::FIXNUM);
                int64_t num_args = resolve_fixnum(tagged_arg_ct);

                // Get the closure
                uint64_t tagged_closure = stk.pop_and_check_type(VT::CLOSURE);
                strip_tag(tagged_closure);
                uint64_t* closure = (uint64_t*) tagged_closure;

                validate_num_args(closure, num_args);

                // Teardown previous locals
                teardown(closure);

                // Overwrite the closure register
                tagged_closure = tagged_closure | CLOSURE_TAG;
                rdi = tagged_closure;
                
                // Push free variables to the stack
                push_free_variables(closure);

                // Jump the PC to the function start
                closure += (2 * WORD_LEN);
                int64_t pc_index = resolve_fixnum(*closure);
                pc = pc_index;
                break;
            }
            case opcode_t::RETURN:
            {
                DEBUG_MSG("RETURN");
                // Pop ret value off the stack
                uint64_t ret_val = stk.pop();

                // Is this the base of the stack? If so we are in a tail call and should finish
                if (rbp == 0) {
                    return std::make_unique<uint64_t>(ret_val);
                }

                // Get the return address
                uint64_t ret_addr = stk.pop_and_check_type(VT::FIXNUM);

                // Restore registers
                rdi = stk.pop();
                rbp = stk.pop();

                // Put the return value back on the stack
                stk.push(ret_val);

                // Jump the pc
                int64_t pc_index = resolve_fixnum(ret_addr);
                pc = pc_index;
                break;
            }
            case opcode_t::PUSH_UNSPEC:
            {
                DEBUG_MSG("PUSH_UNSPEC");
                stk.push(UNSPEC_VAL);
                break;
            }
            case opcode_t::FINISH:
            {
                DEBUG_MSG("FINISH");
                if (stk.empty()) {
                    return nullptr; 
                }
                uint64_t value = stk.pop();
                return std::make_unique<uint64_t>(value);
            }
            default:
            {
               throw std::runtime_error(std::format("Tried to operate on unknown instruction (opcode {})", instr));
            }
        }
    }
    throw std::runtime_error("Code finished without return.");
}

std::vector<uint8_t> read_code() {
    uint8_t buf[4096];
    std::vector<uint8_t> code;

    int n;
    while ((n = read(0, buf, sizeof(buf))) > 0) {
        for (int i = 0; i < n; i++) {
            code.push_back(buf[i]);
        }
    }

    return code;
}

int main() {
    std::vector<uint8_t> code = read_code();
    std::unique_ptr<uint64_t> result_ptr = interpret(code);

    // Validate the ptr
    if (result_ptr) {
        std::cout << value_to_string(*result_ptr) << std::endl;
    }

    return 0;
}