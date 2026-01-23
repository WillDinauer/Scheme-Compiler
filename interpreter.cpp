#include <iostream>
#include <unistd.h>
#include <vector>
#include <memory>
#include <variant>
#include <stdexcept>
#include <format>
#include <iomanip>

// Debug flag and message
#define DEBUG_ACTIVE

#ifdef DEBUG_ACTIVE
    #define DEBUG_MSG(m) do {std::cout << m << std::endl;} while(0)
#else
    #define DEBUG_MSG(m) do {} while(0)
#endif

// # of bytes per word
#define WORD_BYTES      8

// Pointer resolution information
#define FIXNUM_MASK     3
#define FIXNUM_TAG      0
#define FIXNUM_SHIFT    2
#define CHAR_MASK       255
#define CHAR_TAG        15
#define CHAR_SHIFT      8
#define BOOL_MASK       127
#define BOOL_TAG        31
#define BOOL_SHIFT      7
#define EL_MASK         255
#define EL_TAG          47
#define EL_SHIFT        0

#define PTR_MASK        7
#define PAIR_TAG        1
#define VECTOR_TAG      2
#define STRING_TAG      3
#define SYMBOL_TAG      5
#define CLOSURE_TAG     6
#define LAST_3_BITS_0  -8

#define T_BOOL_VAL      1
#define F_BOOL_VAL      0
#define TRUE_BOOL       ((T_BOOL_VAL) << BOOL_SHIFT | BOOL_TAG)
#define FALSE_BOOL      ((F_BOOL_VAL) << BOOL_SHIFT | BOOL_TAG)

// Value Type
enum VT {
    FIXNUM,
    BOOL,
    CHAR,
    EMPTY_LIST,
    PAIR,
    VECTOR,
    STRING,
    SYMBOL,
    CLOSURE,
    UNKNOWN
};

// 1 byte opcodes
enum opcode_t : uint8_t {
    LOAD64 = 0x01,
    RETURN = 0x02,

    // Unary functions
    ADD1 = 0x03,
    SUB1 = 0x04,
    INT_TO_CHAR = 0x05,
    CHAR_TO_INT = 0x06,
    NULL_CHECK = 0x07,
    ZERO_CHECK = 0x08,
    INT_CHECK = 0x09,
    BOOL_CHECK = 0x0A,
    NOT = 0x0B,

    // Binary functions
    ADD = 0x0C,
    SUB = 0x0D,
    MUL = 0x0E,
    LT = 0x0F,
    EQL = 0x10,

    // For local variables
    GET = 0x11,
    DROP = 0x12,
    SQUASH = 0x13,

    // Conditionals
    JMP = 0x14,
    JIF = 0x15,

    // Cons
    CONS = 0x16,
    CAR = 0x17,
    CDR = 0x18,
};

uint64_t create_fixnum_ptr(uint64_t num) {
    return (num << FIXNUM_SHIFT) | FIXNUM_TAG;
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
    throw std::runtime_error(std::format("Unable to resolve type for value: {}", value));
}

// Check if value matches expected type. Throw an error if not
void type_check_or_fail(uint64_t value, VT desired_type) {
    VT type = resolve_type(value);
    if (type != desired_type) {
        throw std::runtime_error("Type check failed."); // This is a non-descript error message and should be fixed...
    }
}

void validate_allocation(uint64_t* hp, uint64_t* heap_end, uint64_t size) {
    if (hp + size > heap_end) {
        throw std::runtime_error("Ran out of heap space.");
    }
}

// Zero out tag for a given pointer
void strip_tag(uint64_t& value) {
    uint64_t shift;
    switch (resolve_type(value)) {
        case VT::FIXNUM:
        {
            shift = FIXNUM_SHIFT;
            break;
        }
        case VT::BOOL:
        {
            shift = BOOL_SHIFT;
            break;
        }
        case VT::CHAR:
        {
            shift = CHAR_SHIFT;
            break;
        }
        case VT::PAIR:
        case VT::VECTOR:
        case VT::STRING:
        case VT::SYMBOL:
        case VT::CLOSURE:
        {
            value &= LAST_3_BITS_0;
            return;
        }
        default:
        {
            throw std::runtime_error("trying to strip unstrippable obj");
        }
    }
    // Zero out tag bits by shifting
    value = (value >> shift) << shift;
}

// Get the value by shifting right the appropriate amount
uint64_t get_fixnum_value(uint64_t value) {
    type_check_or_fail(value, VT::FIXNUM);
    return value >> FIXNUM_SHIFT;
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

// Convert true/false to #t or #f, respectively
std::string cpp_bool_to_scheme_bool(bool value) {
    return value ? "#t" : "#f";
}

// 8-byte stack values
class v_stack {
private:
    std::vector<uint64_t> s;
public:
    void push(uint64_t value) {
        s.push_back(value);
    }

    bool empty() {
        return s.empty();
    }

    uint64_t pop() {
        if (s.size() <= 0) {
            throw std::runtime_error("attempt to pop from empty stack.");
        }
        uint64_t value = s.back();
        s.pop_back();
        return value;
    }

    uint64_t pop_and_check_type(VT type) {
        uint64_t value = pop();
        type_check_or_fail(value, type);
        return value;
    }

    uint64_t get_value_from_top(uint64_t index) {
        if (index > s.size() or s.size() <= 0) {
            throw std::runtime_error(std::format("index {} too great for stack size: {}", index, s.size()));
        }
        return s[(s.size()-1) - index];
    }

    void print_state() {
        std::cout << "[ ";
        for (uint64_t v: s) {
            std::cout << v << " ";
        }
        std::cout << "]" << std::endl;
    }
};

// Read a qword from the code
uint64_t read_word(size_t& pc, std::vector<uint8_t>& code) {
    int bits_per_byte = 8;
    uint64_t ret = 0;

    // Read in bytes 1 at a time, little-endian
    for (int i = 0; i < WORD_BYTES; i++) {
        uint64_t b = (uint64_t)code[pc] << (i * bits_per_byte);
        ret |= b;
        pc++;
    }

    return ret;
}

// Run the code
std::unique_ptr<uint64_t> interpret(std::vector<uint8_t>& code) {
    size_t pc = 0;
    v_stack stk;

    static uint64_t heap[1024];
    uint64_t* hp = heap;
    uint64_t* heap_end = hp + 1024;

    while (pc < code.size()) {
        DEBUG_MSG(std::format("pc: {}", pc));
        #ifdef DEBUG_ACTIVE
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
                uint64_t value = stk.pop_and_check_type(VT::FIXNUM);

                value += (1 << FIXNUM_SHIFT);
                stk.push(value);
                break;
            }
            case opcode_t::SUB1:
            {
                DEBUG_MSG("SUB1");
                uint64_t value = stk.pop_and_check_type(VT::FIXNUM);

                value -= (1 << FIXNUM_SHIFT);
                stk.push(value);
                break;
            }
            case opcode_t::INT_TO_CHAR:
            {
                DEBUG_MSG("INT_TO_CHAR");
                uint64_t value = stk.pop_and_check_type(VT::FIXNUM);

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

                value = value >> CHAR_SHIFT;    // Remove char tag
                value = value << FIXNUM_SHIFT;  // Make space for fixnum tag
                value |= FIXNUM_TAG;            // Add fixnum tag
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
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::FIXNUM);

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

                // Remove tag
                strip_tag(v1);

                // Add and push
                v2 += v1;

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

                // Sub and push
                v2 -= v1;
                stk.push(v2);
                break;
            }
            case opcode_t::MUL:
            {
                DEBUG_MSG("MUL");
                uint64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t v2 = stk.pop_and_check_type(VT::FIXNUM);

                v1 = get_fixnum_value(v1);
                v2 = get_fixnum_value(v2);
                v1 *= v2;
                uint64_t res = create_fixnum_ptr(v1);
                stk.push(res);
                break;
            }
            case opcode_t::LT:
            {
                DEBUG_MSG("LT");
                uint64_t v1 = stk.pop_and_check_type(VT::FIXNUM);
                uint64_t v2 = stk.pop_and_check_type(VT::FIXNUM);
                
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
            case opcode_t::GET:
            {
                DEBUG_MSG("GET");
                uint64_t value = read_word(pc, code);

                // Value becomes an index to reach into on the stack
                value = get_fixnum_value(value);
                #ifdef DEBUG_ACTIVE
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
                uint64_t jump_length = read_word(pc, code);
                type_check_or_fail(jump_length, VT::FIXNUM);
                pc += get_fixnum_value(jump_length);
                break;
            }
            case opcode_t::JIF:
            {
                DEBUG_MSG("JIF");
                uint64_t jump_length = read_word(pc, code);
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                if (type == VT::BOOL && !resolve_bool(value)) {
                    DEBUG_MSG("JUMP IN JIF...(condition == '#f')");
                    type_check_or_fail(jump_length, VT::FIXNUM);
                    pc += get_fixnum_value(jump_length);
                }
                break;
            }
            case opcode_t::CONS:
            {
                DEBUG_MSG("CONS");
                validate_allocation(hp, heap_end, 2*WORD_BYTES);

                // Grab CAR and CDR
                uint64_t cdr = stk.pop();
                uint64_t car = stk.pop();
                
                // Place onto heap
                *hp = car;
                *(hp + WORD_BYTES) = cdr;

                // Put addr on stack and update heap ptr
                uint64_t addr = (uint64_t) hp | PAIR_TAG;
                hp += (2 * WORD_BYTES);
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
                uint64_t* addr = (uint64_t*) tagged_ptr + WORD_BYTES;
                stk.push(*addr);
                break;
            }
            case opcode_t::RETURN:
            {
                DEBUG_MSG("RETURN");
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
        uint64_t result = *result_ptr;
        VT type = resolve_type(result);
        switch(type) {
            case VT::FIXNUM:
            {
                std::cout << (result >> FIXNUM_SHIFT) << std::endl;
                break;
            }
            case VT::BOOL:
            {
                bool truth_val = resolve_bool(result);
                std::cout << cpp_bool_to_scheme_bool(truth_val) << std::endl;
                break;
            }
            case VT::CHAR:
            {
                char c = resolve_char(result);
                std::cout << c << std::endl;
                break;
            }
            case VT::PAIR:
            {
                std::cout << "[INTERPRETER] Printer: Not handling cons blocks yet." << std::endl;
                break;
            }
            default:
            {
                throw std::runtime_error(std::format("Unknown type returned! Raw value: {}", result));
            }
        }
        return 0;
    }
}