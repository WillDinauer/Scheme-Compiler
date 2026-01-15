CXX=g++
TARGET=interpreter
SRC=interpreter.cpp
FLAGS= -Wall -Wextra -Werror -std=c++20 -g -fdiagnostics-color=always

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(FLAGS) -c $(SRC) -o $(TARGET)

clean:
	rm -f $(TARGET)