#include <vector>

#ifndef INTERPRETER_H
#define INTERPRETER_H
// Debug flag and message

#ifdef DEBUG
    #define DEBUG_MSG(m) do {std::cout << m << std::endl;} while(0)
#else
    #define DEBUG_MSG(m) do {} while(0)
#endif  // DEBUG

// # of bytes per word
#define WORD_LEN      8
#define CLOSURE_LEN   3

// -- Pointer resolution information -- 
// Primitives
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
#define UNSPEC_VAL      -1

// Ptrs
#define PTR_MASK        7
#define PAIR_TAG        1
#define VECTOR_TAG      2
#define STRING_TAG      3
#define SYMBOL_TAG      5
#define CLOSURE_TAG     6

// Tag stripping info
#define FIXNUM_NUKE     -1
#define CHAR_NUKE       -16
#define BOOL_NUKE       -32
#define PTR_NUKE        -8

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
    UNSPECIFIED,
    UNKNOWN
};

// 1 byte opcodes
enum opcode_t : uint8_t {
    LOAD64 = 0x01,
    FINISH = 0x02,

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
    KLEG = 0x11,

    // For local variables
    GET = 0x12,
    DROP = 0x13,
    SQUASH = 0x14,

    // Conditionals
    JMP = 0x15,
    JIF = 0x16,

    // Cons
    CONS = 0x17,
    CAR = 0x18,
    CDR = 0x19,

    // String
    ALLOC_STR = 0x1A,
    STR_REF = 0x1B,
    STR_SET = 0x1C,
    STR_APPEND = 0x1D,

    // Vector
    ALLOC_VEC = 0x1E,
    VEC_REF = 0x1F,
    VEC_SET = 0x20,
    VEC_APPEND = 0x21,

    // CLOSURE
    ALLOC_CLO = 0x22,
    GET_CLOSURE = 0x23,

    // Function calls
    FUNCALL = 0x24,
    TAILCALL = 0x25,
    RETURN = 0x26,

    // Unknown
    PUSH_UNSPEC = 0x27,

    // Symbols
    TO_SYMBOL = 0x28,

    // Set
    SET = 0x29,
};

// Type resolution and checking
std::string type_to_string(VT type);
VT resolve_type(uint64_t value);
void strip_tag(uint64_t& value);
void type_check_or_fail(uint64_t value, VT desired_type);
bool resolve_bool(uint64_t value);
char resolve_char(uint64_t value);
int64_t resolve_fixnum(int64_t value);
std::string resolve_string(uint64_t value);
std::string vector_to_string(uint64_t value);
std::string cpp_bool_to_scheme_bool(bool value);

// Ptr creation
int64_t create_fixnum_ptr(int64_t num);
uint64_t create_char_ptr(char c);

// Value display
std::string value_to_string(uint64_t value, bool include_type=false);

// Functions operating on code
std::vector<uint8_t> read_code();
uint64_t read_word(size_t& pc, std::vector<uint8_t>& code);
std::unique_ptr<uint64_t> interpret(std::vector<uint8_t>& code);

// Heap functions for allocation and indexing
void validate_allocation(uint64_t size);
void heap_write_word(uint64_t value);
void align_heap();
char *get_char_ptr(uint64_t idx_value, uint64_t str_value);
uint64_t *get_vector_ptr(uint64_t idx_ptr, uint64_t vec_ptr);

// 8-byte stack values (64-bit)
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

    size_t size() {
        return s.size();
    }

    uint64_t pop() {
        if (s.size() <= 0) {
            throw std::runtime_error("attempt to pop from empty stack.");
        }
        uint64_t value = s.back();
        s.pop_back();
        return value;
    }

    void overwrite_from_base(int64_t src, int64_t dst) {
        if ((size_t) src >= s.size() || src < 0 || (size_t) dst >= s.size() || dst < 0) {
            throw std::runtime_error(std::format("invalid index into stack for call to 'overwrite' - src: {} | dst: {} | size: {}", src, dst, s.size()));
        }
        s[dst] = s[src];
    }

    void replace(int64_t pos, uint64_t value) {
        size_t idx = s.size() - pos - 1;
        if (idx >= s.size() || idx < 0) {
            throw std::runtime_error("invalid index into stack for call to 'replace'");
        }
        s[idx] = value;
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
        std::cout << "STACK: { ";
        for (uint64_t v: s) {
            std::cout << value_to_string(v, true) << " ";
        }
        std::cout << "}" << std::endl;
    }
};

v_stack stk;
uint64_t rdi;
uint64_t rbp;


#endif // INTERPRETER_H