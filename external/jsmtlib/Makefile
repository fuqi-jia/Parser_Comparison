# jSMTLIB Java Parser Makefile

# Java编译器设置
JAVAC = javac
JAVA = java
JAR = jar

# jSMTLIB设置
JSMTLIB_DIR = jSMTLIB-0.9.10.1/SMT
JSMTLIB_SRC = $(JSMTLIB_DIR)/src
JSMTLIB_BUILD = $(JSMTLIB_DIR)

# 类路径设置 - 包含jSMTLIB源码和当前目录
CLASSPATH = "$(JSMTLIB_SRC):."

# 源文件和目标
SOURCE = jsmtlib_parser.java
TARGET = jsmtlib_parser.class
MAIN_CLASS = jsmtlib_parser

# Java编译选项
JAVAC_FLAGS = -cp $(CLASSPATH) -Xlint:unchecked

# 默认目标
all: $(TARGET)

# 编译Java类
$(TARGET): $(SOURCE)
	@echo "编译jSMTLIB解析器..."
	$(JAVAC) $(JAVAC_FLAGS) $(SOURCE)
	@echo "编译完成！"

# 清理生成文件
clean:
	@echo "清理文件..."
	rm -f *.class *.jar manifest.txt test.smt2
	@echo "清理完成！"

# 运行解析器
run: $(TARGET)
	@if [ -z "$(FILE)" ]; then \
		echo "用法: make run FILE=<smt文件>"; \
		echo "示例: make run FILE=test.smt2"; \
	else \
		echo "运行jSMTLIB解析器: $(FILE)"; \
		$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) $(FILE); \
	fi

# 快速测试
test: $(TARGET)
	@echo "测试jSMTLIB解析器..."
	@echo "创建测试文件..."
	@echo "(set-logic QF_UF)" > test.smt2
	@echo "(declare-fun p () Bool)" >> test.smt2
	@echo "(declare-fun q () Bool)" >> test.smt2
	@echo "(assert (and p (not q)))" >> test.smt2
	@echo "(check-sat)" >> test.smt2
	@echo "(exit)" >> test.smt2
	@echo "解析测试文件..."
	$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2

# 检查依赖和环境
check-deps:
	@echo "检查jSMTLIB依赖..."
	@echo "======================"
	@if [ -d "$(JSMTLIB_SRC)" ]; then \
		echo "✓ jSMTLIB源码目录: $(JSMTLIB_SRC)"; \
	else \
		echo "✗ jSMTLIB源码目录不存在: $(JSMTLIB_SRC)"; \
		echo "  请确保jSMTLIB已正确解压"; \
		exit 1; \
	fi
	@if [ -f "$(JSMTLIB_SRC)/org/smtlib/SMT.java" ]; then \
		echo "✓ jSMTLIB核心类文件存在"; \
	else \
		echo "✗ jSMTLIB核心类文件不存在"; \
		echo "  请检查jSMTLIB安装"; \
		exit 1; \
	fi
	@if [ -f "$(SOURCE)" ]; then \
		echo "✓ 解析器源文件: $(SOURCE)"; \
	else \
		echo "✗ 解析器源文件不存在: $(SOURCE)"; \
		exit 1; \
	fi
	@echo "检查Java环境..."
	@echo "==============="
	@if which $(JAVAC) > /dev/null 2>&1; then \
		echo "✓ Java编译器: $$($(JAVAC) -version 2>&1)"; \
	else \
		echo "✗ Java编译器未找到"; \
		echo "  请安装JDK"; \
		exit 1; \
	fi
	@if which $(JAVA) > /dev/null 2>&1; then \
		echo "✓ Java运行时: $$($(JAVA) -version 2>&1 | head -1)"; \
	else \
		echo "✗ Java运行时未找到"; \
		exit 1; \
	fi
	@echo "所有依赖检查通过！"

# 创建可执行JAR包
jar: $(TARGET)
	@echo "创建可执行JAR包..."
	@echo "Main-Class: $(MAIN_CLASS)" > manifest.txt
	$(JAR) cfm jsmtlib_parser.jar manifest.txt *.class
	@rm -f manifest.txt
	@echo "✓ 创建成功: jsmtlib_parser.jar"
	@echo "使用方法: java -cp $(CLASSPATH):jsmtlib_parser.jar $(MAIN_CLASS) <文件名>"

# 编译jSMTLIB库（如果需要）
compile-jsmtlib:
	@echo "编译jSMTLIB库..."
	@if [ -d "$(JSMTLIB_SRC)" ]; then \
		cd $(JSMTLIB_SRC) && find . -name "*.java" -exec $(JAVAC) {} +; \
		echo "✓ jSMTLIB库编译完成"; \
	else \
		echo "✗ jSMTLIB源码目录不存在"; \
		exit 1; \
	fi

# 强制重新编译
rebuild: clean all

# 显示配置信息
info:
	@echo "jSMTLIB Java解析器配置信息"
	@echo "=========================="
	@echo "jSMTLIB目录: $(JSMTLIB_DIR)"
	@echo "源码目录:   $(JSMTLIB_SRC)"
	@echo "类路径:     $(CLASSPATH)"
	@echo "源文件:     $(SOURCE)"
	@echo "目标文件:   $(TARGET)"
	@echo "主类:       $(MAIN_CLASS)"
	@echo "Java编译器: $(JAVAC)"
	@echo "Java运行时: $(JAVA)"

# 帮助信息
help:
	@echo "jSMTLIB Java解析器 Makefile"
	@echo "=========================="
	@echo ""
	@echo "常用目标:"
	@echo "  all           - 编译解析器（默认）"
	@echo "  test          - 运行快速测试"
	@echo "  run FILE=文件  - 解析指定SMT文件"
	@echo "  clean         - 清理生成文件"
	@echo "  check-deps    - 检查依赖和环境"
	@echo ""
	@echo "高级目标:"
	@echo "  jar           - 创建可执行JAR包"
	@echo "  rebuild       - 强制重新编译"
	@echo "  compile-jsmtlib - 编译jSMTLIB库"
	@echo "  info          - 显示配置信息"
	@echo "  help          - 显示此帮助"
	@echo ""
	@echo "使用示例:"
	@echo "  make                    # 编译解析器"
	@echo "  make test               # 运行测试"
	@echo "  make run FILE=test.smt2 # 解析文件"
	@echo "  make check-deps         # 检查环境"
	@echo "  make jar                # 创建JAR包"
	@echo ""
	@echo "故障排除:"
	@echo "  如果编译失败，首先运行: make check-deps"
	@echo "  如果jSMTLIB库有问题，运行: make compile-jsmtlib"

# Debug版本（包含调试信息）
debug: JAVAC_FLAGS += -g -verbose
debug: clean $(TARGET)
	@echo "✓ Debug版本编译完成"

# 详细输出版本
verbose: JAVAC_FLAGS += -verbose
verbose: $(TARGET)

.PHONY: all clean run test check-deps jar compile-jsmtlib rebuild info help debug verbose
