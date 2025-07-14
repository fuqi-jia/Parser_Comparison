# ANTLR4 SMT Parser

基于ANTLR4的SMT-LIB v2解析器实现，用于解析SMT-LIB格式文件并提供性能指标。

## 📁 项目结构

```
external/antlr4_parser/
├── antlr4_parser.java          # 主解析器实现
├── Makefile                    # 构建脚本
├── README.md                   # 本文档
├── smtlibv2-grammar/           # SMT-LIB v2语法文件
│   └── src/main/resources/
│       └── SMTLIBv2.g4        # ANTLR4语法定义
├── antlr4-4.13.2/             # ANTLR4运行时（构建后生成）
└── 生成的Java文件...          # 从语法文件生成的代码
```

## 🚀 快速开始

### 1. 设置环境

```bash
# 设置ANTLR4环境（下载运行时JAR）
make setup-antlr4

# 检查依赖
make check-deps
```

### 2. 生成和编译

```bash
# 从语法文件生成Java代码
make generate

# 编译解析器
make

# 或者一步完成所有操作
make build-and-test
```

### 3. 运行测试

```bash
# 运行详细测试
make test-detailed

# 运行快速测试
make test

# 测试复杂文件
make test-complex
```

## 📊 功能特性

### 核心功能
- **完整的SMT-LIB v2支持**：基于官方语法规范
- **精确的AST节点计数**：递归遍历解析树
- **性能指标测量**：解析时间、内存使用
- **错误处理**：详细的语法错误报告
- **JSON输出**：标准化的结果格式

### 输出格式
```json
{
  "success": true,
  "parse_time": 15.234,
  "memory_usage": 1024,
  "ast_node_count": 42,
  "parsing_method": "antlr4_parse_tree",
  "errors": []
}
```

## 🛠️ 构建和使用

### Makefile目标

#### 安装和设置
```bash
make setup-antlr4      # 设置ANTLR4环境
make check-deps        # 检查依赖
make generate          # 生成Java代码
```

#### 构建
```bash
make all               # 构建解析器（默认）
make clean             # 清理生成文件
make clean-all         # 深度清理
```

#### 测试
```bash
make test              # 快速测试
make test-detailed     # 详细测试
make test-complex      # 复杂文件测试
make create-test       # 创建测试文件
```

#### 运行
```bash
make run FILE=your_file.smt2    # 解析指定文件
java -cp "antlr4-4.13.2/antlr-4.13.2-complete.jar:." antlr4_parser your_file.smt2
```

## 📋 使用示例

### 基本用法
```bash
# 解析SMT文件
./antlr4_parser example.smt2

# 或使用Java直接运行
java -cp "antlr4-4.13.2/antlr-4.13.2-complete.jar:." antlr4_parser example.smt2
```

### 示例输出
```json
{
  "success": true,
  "parse_time": 12.5,
  "memory_usage": 512,
  "ast_node_count": 28,
  "parsing_method": "antlr4_parse_tree",
  "errors": []
}
```

## 🔧 技术实现

### 解析流程
1. **词法分析**：`SMTLIBv2Lexer` 将输入转换为token流
2. **语法分析**：`SMTLIBv2Parser` 构建解析树
3. **AST遍历**：递归计算解析树节点数量
4. **性能测量**：记录时间和内存使用

### 关键组件

#### ASTNodeCounter
```java
public static long countNodes(ParseTree tree) {
    if (tree == null) return 0;
    
    long count = 1; // 当前节点
    
    // 递归计算子节点
    for (int i = 0; i < tree.getChildCount(); i++) {
        count += countNodes(tree.getChild(i));
    }
    
    return count;
}
```

#### 错误处理
```java
parser.addErrorListener(new BaseErrorListener() {
    @Override
    public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol,
                          int line, int charPositionInLine, String msg, RecognitionException e) {
        parseErrors.add("语法错误 第" + line + "行:" + charPositionInLine + " " + msg);
    }
});
```

## 📈 性能特性

### 测量指标
- **解析时间**：纳秒级精度，输出为毫秒
- **内存使用**：堆内存使用差值（KB）
- **AST节点数**：解析树的总节点数量

### 性能优化
- 使用ANTLR4的高效解析算法
- 最小化内存分配
- 递归优化的节点计数

## 🔍 与其他解析器的比较

| 特性 | ANTLR4 | Z3 | CVC5 | jSMTLIB |
|------|---------|-----|------|---------|
| 语法完整性 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| 节点计数 | ✅ 精确 | ✅ 精确 | ✅ 精确 | ✅ 精确 |
| 错误处理 | ✅ 详细 | ✅ 详细 | ✅ 详细 | ✅ 详细 |
| 性能测量 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 |

## 🐛 故障排除

### 常见问题

1. **ANTLR4运行时不存在**
   ```bash
   make setup-antlr4
   ```

2. **语法文件找不到**
   ```bash
   # 确保smtlibv2-grammar目录存在
   ls smtlibv2-grammar/src/main/resources/SMTLIBv2.g4
   ```

3. **编译错误**
   ```bash
   # 清理并重新构建
   make clean
   make generate
   make
   ```

4. **Java内存不足**
   ```bash
   # 增加Java堆内存
   java -Xmx2g -cp "antlr4-4.13.2/antlr-4.13.2-complete.jar:." antlr4_parser your_file.smt2
   ```

## 📚 参考资料

- [ANTLR4官方文档](https://www.antlr.org/)
- [SMT-LIB v2规范](http://smtlib.cs.uiowa.edu/papers/smt-lib-reference-v2.6-r2017-07-18.pdf)
- [SMT-LIB v2语法项目](https://github.com/julianthome/smtlibv2-grammar)

## 📄 许可证

本项目遵循MIT许可证。SMT-LIB v2语法文件来自[smtlibv2-grammar项目](https://github.com/julianthome/smtlibv2-grammar)。 