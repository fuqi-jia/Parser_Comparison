#!/bin/bash

# ANTLR4 SMT Parser 设置脚本
# 自动化设置ANTLR4环境并构建解析器

set -e  # 遇到错误时退出

echo "=== ANTLR4 SMT Parser 设置脚本 ==="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
git clone https://github.com/julianthome/smtlibv2-grammar.git
ANTLR4_VERSION="4.13.2"
ANTLR4_JAR="antlr4-${ANTLR4_VERSION}/antlr-${ANTLR4_VERSION}-complete.jar"
ANTLR4_URL="https://www.antlr.org/download/antlr-${ANTLR4_VERSION}-complete.jar"
GRAMMAR_FILE="smtlibv2-grammar-master/src/main/resources/SMTLIBv2.g4"

# 辅助函数
print_step() {
    echo -e "${BLUE}[步骤]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "命令 '$1' 未找到，请先安装"
        exit 1
    fi
}

# 检查基本依赖
print_step "检查基本依赖..."
check_command "java"
check_command "javac"
check_command "make"

# 检查Java版本
JAVA_VERSION=$(java -version 2>&1 | grep -oP 'version "?(1\.)?\K\d+' | head -1)
if [ "$JAVA_VERSION" -lt 8 ]; then
    print_error "需要Java 8或更高版本，当前版本: $JAVA_VERSION"
    exit 1
fi
print_success "Java版本检查通过 (版本: $JAVA_VERSION)"

# 检查语法文件
print_step "检查语法文件..."
if [ ! -f "$GRAMMAR_FILE" ]; then
    print_error "语法文件不存在: $GRAMMAR_FILE"
    print_error "请确保smtlibv2-grammar目录存在"
    exit 1
fi
print_success "语法文件找到: $GRAMMAR_FILE"

# 设置ANTLR4环境
print_step "设置ANTLR4环境..."
if [ ! -f "$ANTLR4_JAR" ]; then
    print_step "创建ANTLR4目录..."
    mkdir -p "antlr4-${ANTLR4_VERSION}"
    
    print_step "下载ANTLR4运行时..."
    if command -v wget &> /dev/null; then
        wget -O "$ANTLR4_JAR" "$ANTLR4_URL"
    elif command -v curl &> /dev/null; then
        curl -o "$ANTLR4_JAR" "$ANTLR4_URL"
    else
        print_error "需要wget或curl来下载ANTLR4运行时"
        print_error "请手动下载 $ANTLR4_URL 到 $ANTLR4_JAR"
        exit 1
    fi
    
    if [ ! -f "$ANTLR4_JAR" ]; then
        print_error "ANTLR4运行时下载失败"
        exit 1
    fi
    print_success "ANTLR4运行时下载完成"
else
    print_success "ANTLR4运行时已存在"
fi

# 生成Java代码
print_step "从语法文件生成Java代码..."
make generate
print_success "Java代码生成完成"

# 编译解析器
print_step "编译解析器..."
make all
print_success "解析器编译完成"

# 运行测试
print_step "运行测试..."
make test-detailed
print_success "测试完成"

echo ""
echo -e "${GREEN}=== 设置完成！ ===${NC}"
echo ""
echo "使用方法："
echo "  make run FILE=your_file.smt2    # 解析指定文件"
echo "  make test                       # 运行测试"
echo "  make help                       # 查看帮助"
echo ""
echo "示例："
echo "  make run FILE=test.smt2"
echo "  java -cp \"$ANTLR4_JAR:.\" antlr4_parser your_file.smt2"
echo ""
echo -e "${BLUE}有关详细信息，请查看 README.md${NC}" 