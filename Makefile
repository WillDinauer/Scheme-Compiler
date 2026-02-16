CXX=g++
TARGET=interpreter
SRC=interpreter.cpp
CXXFLAGS= -Wall -Wextra -Werror -Wpedantic -Wvla -Wshadow -fsanitize=address,undefined -std=c++20 -g -fdiagnostics-color=always

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

debug: $(SRC)
	$(CXX) $(CXXFLAGS) -DDEBUG $(SRC) -o $(TARGET)

clean:
	rm -f $(TARGET) code.txt compiled.bc