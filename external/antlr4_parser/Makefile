# ANTLR4 SMT Parser Makefile

# Java编译器设置
JAVAC = javac
JAVA = java
JAR = jar

# ANTLR4设置
ANTLR4_VERSION = 4.13.2
# 检查多个可能的JAR位置
ANTLR4_JAR_LOCAL = antlr-$(ANTLR4_VERSION)-complete.jar
ANTLR4_JAR_DIR = antlr4-$(ANTLR4_VERSION)/antlr-$(ANTLR4_VERSION)-complete.jar
ANTLR4_JAR_EXTRACTED = antlr4-4.13.2/antlr-4.13.2-complete.jar
ANTLR4_URL = https://www.antlr.org/download/antlr-$(ANTLR4_VERSION)-complete.jar

# 自动检测可用的JAR文件
ANTLR4_JAR = $(shell \
	if [ -f "$(ANTLR4_JAR_LOCAL)" ]; then \
		echo "$(ANTLR4_JAR_LOCAL)"; \
	elif [ -f "$(ANTLR4_JAR_EXTRACTED)" ]; then \
		echo "$(ANTLR4_JAR_EXTRACTED)"; \
	elif [ -f "$(ANTLR4_JAR_DIR)" ]; then \
		echo "$(ANTLR4_JAR_DIR)"; \
	else \
		echo "$(ANTLR4_JAR_DIR)"; \
	fi)

# 语法文件设置
GRAMMAR_FILE = SMTLIBv2.g4
GRAMMAR_SRC = smtlibv2-grammar/src/main/resources/$(GRAMMAR_FILE)
GRAMMAR_LOCAL = $(GRAMMAR_FILE)

# 生成的Java文件
GENERATED_FILES = SMTLIBv2BaseListener.java SMTLIBv2Lexer.java SMTLIBv2Listener.java SMTLIBv2Parser.java

# 类路径设置
CLASSPATH = "$(ANTLR4_JAR):."

# 源文件和目标
SOURCE = antlr4_parser.java
TARGET = antlr4_parser.class
MAIN_CLASS = antlr4_parser

# Java编译选项
JAVAC_FLAGS = -cp $(CLASSPATH) -Xlint:unchecked

# 默认目标
all: $(TARGET)

# 检查依赖
check-deps:
	@echo "检查ANTLR4依赖..."
	@if [ -f "$(ANTLR4_JAR_LOCAL)" ]; then \
		echo "✓ ANTLR4运行时找到: $(ANTLR4_JAR_LOCAL)"; \
	elif [ -f "$(ANTLR4_JAR_EXTRACTED)" ]; then \
		echo "✓ ANTLR4运行时找到: $(ANTLR4_JAR_EXTRACTED)"; \
	elif [ -f "$(ANTLR4_JAR_DIR)" ]; then \
		echo "✓ ANTLR4运行时找到: $(ANTLR4_JAR_DIR)"; \
	else \
		echo "✗ ANTLR4运行时未找到"; \
		echo "请将 antlr-$(ANTLR4_VERSION)-complete.jar 放在以下位置之一:"; \
		echo "  - 当前目录: $(ANTLR4_JAR_LOCAL)"; \
		echo "  - 解压目录: $(ANTLR4_JAR_EXTRACTED)"; \
		echo "  - 或运行: make setup-antlr4 自动下载"; \
		exit 1; \
	fi
	@if [ ! -f "$(GRAMMAR_SRC)" ]; then \
		echo "✗ 语法文件不存在: $(GRAMMAR_SRC)"; \
		echo "请确保smtlibv2-grammar目录存在"; \
		exit 1; \
	else \
		echo "✓ 语法文件找到: $(GRAMMAR_SRC)"; \
	fi
	@echo "✓ 使用的ANTLR4 JAR: $(ANTLR4_JAR)"

# 设置ANTLR4环境
setup-antlr4:
	@echo "设置ANTLR4环境..."
	@# 检查是否已经有JAR文件
	@if [ -f "$(ANTLR4_JAR_LOCAL)" ]; then \
		echo "✓ 在当前目录找到ANTLR4运行时: $(ANTLR4_JAR_LOCAL)"; \
	elif [ -f "$(ANTLR4_JAR_EXTRACTED)" ]; then \
		echo "✓ 在解压目录找到ANTLR4运行时: $(ANTLR4_JAR_EXTRACTED)"; \
	elif [ -f "4.13.2.zip" ]; then \
		echo "找到ANTLR4压缩包，正在解压..."; \
		mkdir -p antlr4-$(ANTLR4_VERSION); \
		unzip -q 4.13.2.zip -d antlr4-$(ANTLR4_VERSION); \
		if [ -f "$(ANTLR4_JAR_EXTRACTED)" ]; then \
			echo "✓ 解压完成: $(ANTLR4_JAR_EXTRACTED)"; \
		else \
			echo "解压后未找到JAR文件，请检查压缩包内容"; \
		fi; \
	else \
		echo "未找到现有的ANTLR4 JAR文件，开始下载..."; \
		mkdir -p antlr4-$(ANTLR4_VERSION); \
		if command -v wget >/dev/null 2>&1; then \
			wget -O $(ANTLR4_JAR_DIR) $(ANTLR4_URL); \
		elif command -v curl >/dev/null 2>&1; then \
			curl -o $(ANTLR4_JAR_DIR) $(ANTLR4_URL); \
		else \
			echo "错误: 需要wget或curl来下载ANTLR4运行时"; \
			echo "请手动下载 $(ANTLR4_URL)"; \
			echo "并将其保存为: $(ANTLR4_JAR_LOCAL)"; \
			exit 1; \
		fi; \
		if [ -f "$(ANTLR4_JAR_DIR)" ]; then \
			echo "✓ 下载完成: $(ANTLR4_JAR_DIR)"; \
		else \
			echo "下载失败，请手动下载"; \
			exit 1; \
		fi; \
	fi
	@echo "ANTLR4环境设置完成！"

# 使用已有的ANTLR4 JAR文件
use-existing-jar:
	@echo "使用已有的ANTLR4 JAR文件..."
	@if [ -z "$(JAR_PATH)" ]; then \
		echo "用法: make use-existing-jar JAR_PATH=<jar文件路径>"; \
		echo "示例: make use-existing-jar JAR_PATH=/path/to/antlr-4.13.2-complete.jar"; \
		exit 1; \
	fi
	@if [ ! -f "$(JAR_PATH)" ]; then \
		echo "错误: JAR文件不存在: $(JAR_PATH)"; \
		exit 1; \
	fi
	@echo "复制JAR文件到当前目录..."
	cp "$(JAR_PATH)" "$(ANTLR4_JAR_LOCAL)"
	@echo "✓ JAR文件已复制: $(ANTLR4_JAR_LOCAL)"

# 复制语法文件
$(GRAMMAR_LOCAL): $(GRAMMAR_SRC)
	@echo "复制语法文件..."
	cp $(GRAMMAR_SRC) $(GRAMMAR_LOCAL)

# 从语法文件生成Java代码
generate: $(GRAMMAR_LOCAL) $(ANTLR4_JAR)
	@echo "从语法文件生成Java代码..."
	$(JAVA) -jar $(ANTLR4_JAR) -visitor -listener $(GRAMMAR_LOCAL)
	@echo "代码生成完成！"

# 编译Java类
$(TARGET): $(GENERATED_FILES) $(SOURCE)
	@echo "编译ANTLR4解析器..."
	$(JAVAC) $(JAVAC_FLAGS) $(GENERATED_FILES) $(SOURCE)
	@echo "编译完成！"

# 生成的文件依赖于generate目标
$(GENERATED_FILES): generate

# 清理生成文件
clean:
	@echo "清理文件..."
	rm -f *.class *.jar manifest.txt test.smt2 complex-test.smt2
	rm -f $(GENERATED_FILES) $(GRAMMAR_LOCAL)
	rm -f *.tokens *.interp
	@echo "清理完成！"

# 深度清理（包括下载的文件）
clean-all: clean
	@echo "深度清理..."
	rm -rf antlr4-$(ANTLR4_VERSION)
	@echo "深度清理完成！"

# 运行解析器
run: $(TARGET)
	@if [ -z "$(FILE)" ]; then \
		echo "用法: make run FILE=<smt文件>"; \
		echo "示例: make run FILE=test.smt2"; \
	else \
		echo "运行ANTLR4解析器: $(FILE)"; \
		$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) $(FILE); \
	fi

# 创建简单测试文件
create-test:
	@echo "创建test.smt2..."
	@echo "(set-logic QF_LIA)" > test.smt2
	@echo "(declare-fun x () Int)" >> test.smt2
	@echo "(declare-fun y () Int)" >> test.smt2
	@echo "(assert (> x 0))" >> test.smt2
	@echo "(assert (< y 10))" >> test.smt2
	@echo "(assert (= (+ x y) 15))" >> test.smt2
	@echo "(check-sat)" >> test.smt2
	@echo "(exit)" >> test.smt2
	@echo "测试文件test.smt2创建完成"

# 创建复杂测试文件
create-complex-test:
	@echo "创建complex-test.smt2..."
	@echo "(set-logic QF_LRA)" > complex-test.smt2
	@echo "(declare-fun x () Real)" >> complex-test.smt2
	@echo "(declare-fun y () Real)" >> complex-test.smt2
	@echo "(declare-fun z () Real)" >> complex-test.smt2
	@echo "(assert (> x 0.0))" >> complex-test.smt2
	@echo "(assert (< y 10.5))" >> complex-test.smt2
	@echo "(assert (= z (+ x y)))" >> complex-test.smt2
	@echo "(assert (>= z 5.0))" >> complex-test.smt2
	@echo "(assert (<= z 15.0))" >> complex-test.smt2
	@echo "(check-sat)" >> complex-test.smt2
	@echo "(exit)" >> complex-test.smt2
	@echo "复杂测试文件complex-test.smt2创建完成"

# 快速测试
test: $(TARGET) create-test
	@echo "=== ANTLR4解析器快速测试 ==="
	@echo "测试文件内容："
	@cat test.smt2
	@echo ""
	@echo "解析结果："
	@$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2

# 测试并格式化输出
test-with-output: $(TARGET) create-test
	@echo "运行ANTLR4解析器测试..."
	@$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2 | python3 -m json.tool 2>/dev/null || (echo "JSON格式化失败，显示原始输出：" && $(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2)

# 详细测试
test-detailed: $(TARGET) create-test
	@echo "=== ANTLR4解析器详细测试 ==="
	@echo "1. 检查依赖..."
	@make check-deps
	@echo ""
	@echo "2. 测试解析器..."
	@echo "测试文件内容："
	@cat test.smt2
	@echo ""
	@echo "3. 原始解析输出："
	@$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2
	@echo ""
	@echo "4. 格式化JSON输出："
	@$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2 | python3 -m json.tool 2>/dev/null || (echo "JSON格式化失败，显示原始输出：" && $(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) test.smt2)

# 测试复杂文件
test-complex: $(TARGET) create-complex-test
	@echo "测试复杂SMT文件..."
	@$(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) complex-test.smt2 | python3 -m json.tool 2>/dev/null || $(JAVA) -cp $(CLASSPATH) $(MAIN_CLASS) complex-test.smt2

# 帮助信息
help:
	@echo "ANTLR4 SMT Parser Makefile"
	@echo ""
	@echo "安装和设置："
	@echo "  setup-antlr4      - 设置ANTLR4环境"
	@echo "  use-existing-jar  - 使用已有的ANTLR4 JAR文件"
	@echo "  check-deps        - 检查依赖"
	@echo "  generate          - 从语法文件生成Java代码"
	@echo ""
	@echo "构建目标："
	@echo "  all               - 构建解析器（默认）"
	@echo "  clean             - 清理生成文件"
	@echo "  clean-all         - 深度清理所有文件"
	@echo ""
	@echo "测试目标："
	@echo "  test              - 运行快速测试"
	@echo "  test-with-output  - 运行测试并格式化输出"
	@echo "  test-detailed     - 运行详细测试"
	@echo "  test-complex      - 测试复杂SMT文件"
	@echo "  create-test       - 创建简单测试文件"
	@echo "  create-complex-test - 创建复杂测试文件"
	@echo ""
	@echo "运行："
	@echo "  run FILE=<文件>   - 运行解析器"
	@echo "  help              - 显示此帮助"
	@echo ""
	@echo "配置："
	@echo "  ANTLR4_VERSION = $(ANTLR4_VERSION)"
	@echo "  ANTLR4_JAR     = $(ANTLR4_JAR)"
	@echo "  GRAMMAR_FILE   = $(GRAMMAR_FILE)"
	@echo ""
	@echo "快速开始："
	@echo "  # 如果你已有ANTLR4 JAR文件："
	@echo "  make use-existing-jar JAR_PATH=<你的jar路径>"
	@echo "  # 或者将JAR文件直接复制为: antlr-4.13.2-complete.jar"
	@echo ""
	@echo "  # 标准流程："
	@echo "  make setup-antlr4  # 设置ANTLR4环境（如果需要）"
	@echo "  make check-deps    # 检查依赖"
	@echo "  make generate      # 生成Java代码"
	@echo "  make               # 构建解析器"
	@echo "  make test-detailed # 运行详细测试"

# 构建和测试的完整流程
build-and-test: setup-antlr4 check-deps generate all test-detailed

.PHONY: all check-deps setup-antlr4 use-existing-jar generate clean clean-all run test test-with-output test-detailed test-complex create-test create-complex-test help build-and-test 