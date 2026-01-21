CXX=g++
TARGET=interpreter
SRC=interpreter.cpp
FLAGS= -Wall -Wextra -Werror -Wpedantic -Wvla -Wshadow -fsanitize=address,undefined -std=c++20 -g -fdiagnostics-color=always

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(FLAGS) $(SRC) -o $(TARGET)

clean:
	rm -f $(TARGET)