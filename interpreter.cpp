#include <iostream>
#include <unistd.h>
#include <vector>
#include <memory>
#include <variant>
#include <stdexcept>
#include <format>
#include <iomanip>

// debug flag
#define DEBUG_ACTIVE

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
enum opcodes : uint8_t {
    LOAD64 = 0x01,
    RETURN = 0x02,
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
    CHAR
};

// Figure out the type based on the tag information
VT resolve_type(uint64_t value) {
    #ifdef DEBUG_ACTIVE
        std::cout << "resolving value: " << value << std::endl;
    #endif

    return VT::FIXNUM;
}

// Run the code
std::unique_ptr<uint64_t> interpret(std::vector<uint8_t>& code) {
    size_t pc = 0;
    v_stack stk;
    while (pc < code.size()) {
        // truncate instr to lowest byte
        uint8_t instr = read_word(pc, code);
        switch(instr) {
            case opcodes::LOAD64:
            {
                #ifdef DEBUG_ACTIVE
                    std::cout << "Load called..." << std::endl;
                #endif
                
                uint64_t value = read_word(pc, code);
                stk.push(value);
                break;
            }
            case opcodes::RETURN:
            {
                #ifdef DEBUG_ACTIVE
                    std::cout << "Return called..." << std::endl;
                #endif

                uint64_t value = stk.pop();
                VT ty = resolve_type(value);
                if (ty == VT::FIXNUM) {
                    return std::make_unique<uint64_t>(value);
                }
                return nullptr;
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
    std::unique_ptr<uint64_t> result = interpret(code);
    if (result) {
        std::cout << *result << std::endl;
    }
}