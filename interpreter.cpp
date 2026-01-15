#include <iostream>
#include <unistd.h>
#include <vector>
#include <memory>
#include <variant>
#include <stdexcept>
#include <format>
#include <iomanip>

// debug flag
// #define DEBUG_ACTIVE

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

#define TRUE_BOOL       (0 | BOOL_TAG)
#define FALSE_BOOL      ((1 << BOOL_SHIFT) | BOOL_TAG)

// From https://stackoverflow.com/questions/6966425/converting-an-uint64-into-a-fullhex-string-c
// Print a formatted 64-bit value
void print_64b(std::string name, uint64_t value) {
    std::cout << name
              << " Padded Hex: 0x"
              << std::setw(16)
              << std::setfill('0')
              << std::hex
              << value
              << std::endl;
}

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
    EQL = 0x10
};

// 8-byte stack values
class v_stack {
private:
    std::vector<uint64_t> s;
public:
    void push(uint64_t value) {
        s.push_back(value);
    }

    uint64_t pop() {
        if (s.size() <= 0) {
            return 0;
        }
        int value = s.back();
        s.pop_back();
        return value;
    }
};

// Read a qword from the code
uint64_t read_word(size_t& pc, std::vector<uint8_t>& code) {
    int word_bytes = 8;
    uint64_t ret = 0;

    // Read in bytes 1 at a time, little-endian
    for (int i = 0; i < word_bytes; i++) {
        uint64_t b = code[pc] << i;
        ret |= b;
        pc++;
    }

    return ret;
}

// Value Type
enum VT {
    FIXNUM,
    BOOL,
    CHAR,
    EMPTY_LIST,
    UNKNOWN
};

// Figure out the type based on the tag information
VT resolve_type(uint64_t value) {
    #ifdef DEBUG_ACTIVE
        std::cout << "resolving value: " << value << std::endl;
    #endif

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
    throw std::runtime_error(std::format("Unable to resolve type for value: {}", value));
}

// Check if value matches expected type. Throw an error if not
void type_check_or_fail(uint64_t value, VT desired_type) {
    VT type = resolve_type(value);
    if (type != desired_type) {
        throw std::runtime_error("Type check failed."); // This is a non-descript error message and should be fixed...
    }
}

// Convert uint64_t representation of boolean to c++ true/false
bool resolve_bool(uint64_t value) {
    type_check_or_fail(value, VT::BOOL);
    return (value >> BOOL_SHIFT) == 0;
}

// Convert true/false to #t or #f, respectively
std::string cpp_bool_to_scheme_bool(bool value) {
    return value ? "#t" : "#f";
}

// Run the code
uint64_t interpret(std::vector<uint8_t>& code) {
    size_t pc = 0;
    v_stack stk;
    while (pc < code.size()) {
        // truncate instr to lowest byte
        uint8_t instr = read_word(pc, code);
        switch(instr) {
            case opcode_t::LOAD64:
            {
                #ifdef DEBUG_ACTIVE
                    std::cout << "Load called..." << std::endl;
                #endif
                
                uint64_t value = read_word(pc, code);
                stk.push(value);
                break;
            }
            case opcode_t::ADD1:
            {
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::FIXNUM);
                
                value += (1 << FIXNUM_SHIFT);
                stk.push(value);
                break;
            }
            case opcode_t::SUB1:
            {
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::FIXNUM);

                value -= (1 << FIXNUM_SHIFT);
                stk.push(value);
                break;
            }
            case opcode_t::INT_TO_CHAR:
            {
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::FIXNUM);

                value = value >> FIXNUM_SHIFT;  // Remove fixnum tag
                value = value << CHAR_SHIFT;    // Make space for char tag
                value |= CHAR_TAG;              // Add char tag
                stk.push(value);
                break;
            }
            case opcode_t::CHAR_TO_INT:
            {
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::CHAR);

                value = value >> CHAR_SHIFT;    // Remove char tag
                value = value << FIXNUM_SHIFT;  // Make space for fixnum tag
                value |= FIXNUM_TAG;            // Add fixnum tag
                stk.push(value);
                break;
            }
            case opcode_t::NULL_CHECK:
            {
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                type == VT::EMPTY_LIST ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::ZERO_CHECK:
            {
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::FIXNUM);

                int zero = 0 | FIXNUM_TAG;
                value == zero ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::INT_CHECK:
            {
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                type == VT::FIXNUM ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::BOOL_CHECK:
            {
                uint64_t value = stk.pop();
                VT type = resolve_type(value);
                type == VT::BOOL ? stk.push(TRUE_BOOL) : stk.push(FALSE_BOOL);
                break;
            }
            case opcode_t::NOT:
            {
                uint64_t value = stk.pop();
                type_check_or_fail(value, VT::BOOL);

                resolve_bool(value) ? stk.push(FALSE_BOOL) : stk.push(TRUE_BOOL);
                break;
            }
            case opcode_t::RETURN:
            {
                #ifdef DEBUG_ACTIVE
                    std::cout << "Return called..." << std::endl;
                #endif

                uint64_t value = stk.pop();
                return value;
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
    int buf_size = 4096;
    uint8_t buf[buf_size];
    std::vector<uint8_t> code;

    int n;
    while ((n = read(0, buf, buf_size)) > 0) {
        for (int i = 0; i < n; i++) {
            code.push_back(buf[i]);
        }
    }

    return code;
}

int main() {
    std::vector<uint8_t> code = read_code();
    uint64_t result = interpret(code);
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
        default:
        {
            throw std::runtime_error(std::format("Unknown type returned! Raw value: {}", result));
        }
    }
    return 0;
}