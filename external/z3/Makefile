# Z3 C++ Parser Makefile
# 支持两种布局：
#   - 预编译包：z3-4.16.0-x64-glibc-2.39/ 含 include/、lib/、bin/
#   - 源码构建：z3-z3-4.15.2/ 含 src/api/c++、build/

CXX ?= g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra

# 自动检测：优先预编译包 z3-*-x64-*，否则 z3-z3-*
Z3_PREBUILT := $(shell ls -d z3-*-x64-* 2>/dev/null | head -1)
Z3_SRC := $(shell ls -d z3-z3-* 2>/dev/null | head -1)

ifneq ($(Z3_PREBUILT),)
  Z3_INCLUDE = $(Z3_PREBUILT)/include
  Z3_LIB = $(shell Z3P="$(Z3_PREBUILT)"; if [ -f "$$Z3P/lib/libz3.so" ] || [ -f "$$Z3P/lib/libz3.a" ]; then echo "$$Z3P/lib"; else echo "$$Z3P/bin"; fi)
  Z3_LIBS = -lz3
  INCLUDES = -I$(Z3_INCLUDE)
  LDFLAGS = -L$(Z3_LIB) -Wl,-rpath,$$ORIGIN/$(Z3_LIB)
else ifneq ($(Z3_SRC),)
  Z3_INCLUDE = $(Z3_SRC)/src/api/c++
  Z3_LIB = $(Z3_SRC)/build
  Z3_LIBS = -lz3
  INCLUDES = -I$(Z3_INCLUDE) -I$(Z3_SRC)/src/api
  LDFLAGS = -L$(Z3_LIB) -Wl,-rpath,$(shell pwd)/$(Z3_LIB)
else
  Z3_INCLUDE ?= /usr/include
  Z3_LIB ?= /usr/lib
  Z3_LIBS = -lz3
  INCLUDES = -I$(Z3_INCLUDE)
  LDFLAGS = -L$(Z3_LIB)
endif

TARGET = z3_parser
SOURCE = z3_parser.cpp
TARGET2 = z3_parse_vs_solve
SOURCE2 = z3_parse_vs_solve.cpp

all: $(TARGET) $(TARGET2)

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $(TARGET) $(SOURCE) $(LDFLAGS) $(Z3_LIBS)

$(TARGET2): $(SOURCE2)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $(TARGET2) $(SOURCE2) $(LDFLAGS) $(Z3_LIBS)

clean:
	rm -f $(TARGET) $(TARGET2) *.o

test: $(TARGET)
	@if [ -f test.smt2 ]; then ./$(TARGET) test.smt2; else echo "No test.smt2"; fi

check-deps:
	@echo "Z3_INCLUDE = $(Z3_INCLUDE)"
	@echo "Z3_LIB = $(Z3_LIB)"
	@test -f "$(Z3_INCLUDE)/z3++.h" || (echo "Missing z3++.h"; exit 1)
	@test -f "$(Z3_LIB)/libz3.so" -o -f "$(Z3_LIB)/libz3.a" || (echo "Missing libz3"; exit 1)
	@echo "OK"

help:
	@echo "Z3 Parser: 预编译 z3-*-x64-* 或源码 z3-z3-*"
	@echo "  make [all]  - 编译 z3_parser 与 z3_parse_vs_solve"
	@echo "  make test   - 运行 test.smt2"
	@echo "  make check-deps - 检查 Z3 路径"

.PHONY: all clean test check-deps help
