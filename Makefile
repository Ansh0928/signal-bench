CXX = c++
CXXFLAGS = -std=c++17 -Wall -Wextra -Wpedantic -Werror -O2
PORT ?= 8873

.PHONY: build test demo serve clean
build: build/controller

build/controller: src/main.cpp src/controller.hpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) src/main.cpp -o $@

test: build
	python3 tests/run_tests.py

demo: test
	python3 tools.py report

serve: demo
	python3 tools.py serve --port $(PORT)

clean:
	rm -rf build
