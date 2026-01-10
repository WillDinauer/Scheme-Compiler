#include <iostream>
#include <unistd.h>
#include <cstddef>
#include <vector>

void interpret(std::vector<std::byte>& code) {
    return;
}

std::vector<std::byte> read_code() {
    int buf_size = 4096;
    std::byte buf[buf_size];

    std::vector<std::byte> code;

    int n;
    while ((n = read(0, buf, buf_size)) > 0) {
        for (int i = 0; i < n; i++) {
            code.push_back(buf[i]);   
        }
    }

    return code;
}

int main() {
    std::vector<std::byte> code = read_code();
    std::cout << "length of code: " << code.size() << std::endl;
    interpret(code);
}