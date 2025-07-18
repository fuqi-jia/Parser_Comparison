# Z3 C++ Parser Makefile

# 编译器设置
CC=$(CONDA_PREFIX)/bin/x86_64-conda-linux-gnu-gcc
CXX=$(CONDA_PREFIX)/bin/x86_64-conda-linux-gnu-g++
# CC=gcc
# CXX=g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra

# Z3库设置
Z3_INCLUDE = z3-z3-4.15.2/src/api/c++
Z3_LIB = z3-z3-4.15.2/build
Z3_LIBS = -lz3

# 包含路径和库路径
INCLUDES = -I$(Z3_INCLUDE) -Iz3-z3-4.15.2/src/api
LDFLAGS = -L$(Z3_LIB) -Wl,-rpath,$(shell pwd)/$(Z3_LIB)

# 目标文件
TARGET = z3_parser
SOURCE = z3_parser.cpp

# 默认目标
all: $(TARGET)

# 编译主程序
$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $(TARGET) $(SOURCE) $(LDFLAGS) $(Z3_LIBS)

# 清理
clean:
	rm -f $(TARGET) *.o

# 安装（可选）
install: $(TARGET)
	cp $(TARGET) /usr/local/bin/

# 卸载（可选）
uninstall:
	rm -f /usr/local/bin/$(TARGET)

# 测试
test: $(TARGET)
	@echo "Testing Z3 parser..."
	@if [ -f test.smt2 ]; then \
		./$(TARGET) test.smt2; \
	else \
		echo "No test.smt2 file found"; \
	fi

# 检查Z3依赖
check-deps:
	@echo "Checking Z3 dependencies..."
	@if [ -f "$(Z3_INCLUDE)/z3++.h" ]; then \
		echo "✓ Z3 C++ headers found"; \
	else \
		echo "✗ Z3 C++ headers not found at $(Z3_INCLUDE)/z3++.h"; \
		echo "Please install Z3 development package or update Z3_INCLUDE path"; \
	fi
	@if [ -f "$(Z3_LIB)/libz3.so" ] || [ -f "$(Z3_LIB)/libz3.a" ]; then \
		echo "✓ Z3 library found"; \
	else \
		echo "✗ Z3 library not found at $(Z3_LIB)"; \
		echo "Please install Z3 library or update Z3_LIB path"; \
	fi

# 帮助信息
help:
	@echo "Z3 C++ Parser Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all       - Build the parser (default)"
	@echo "  clean     - Remove built files"
	@echo "  test      - Run a simple test"
	@echo "  install   - Install to /usr/local/bin"
	@echo "  uninstall - Remove from /usr/local/bin"
	@echo "  check-deps- Check Z3 dependencies"
	@echo "  help      - Show this help"
	@echo ""
	@echo "Configuration:"
	@echo "  Z3_INCLUDE = $(Z3_INCLUDE)"
	@echo "  Z3_LIB     = $(Z3_LIB)"
	@echo "  Z3_LIBS    = $(Z3_LIBS)"
	@echo ""
	@echo "To use custom Z3 installation:"
	@echo "  make Z3_INCLUDE=/path/to/include Z3_LIB=/path/to/lib"

# Debug版本
debug: CXXFLAGS += -g -DDEBUG
debug: $(TARGET)

# 静态链接版本
static: LDFLAGS += -static
static: $(TARGET)

.PHONY: all clean install uninstall test check-deps help debug static
