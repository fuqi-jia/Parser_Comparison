# SMT解析器性能比较工具

这个项目提供了一个框架，用于比较不同SMT-LIB解析器的性能和功能。

## 支持的解析器

- 原生SMT-LIB解析器
- pySMT解析器
- ANTLR SMT-LIB解析器
- jSMTLIB解析器
- SWI-Prolog SMT-LIB解析器

## 对比指标

- 解析时间（毫秒）
- 内存占用（KB）
- AST节点数量
- 语法覆盖率
- 语义检查能力
- 解析成功率

## 构建项目

```bash
mkdir build && cd build
cmake ..
make
```

## 使用方法

### 列出可用的解析器

```bash
./smt_parser_comparison list
```

### 测试单个文件

```bash
./smt_parser_comparison test --file path/to/file.smt2
```

### 对比多个文件的性能

```bash
./smt_parser_comparison benchmark --file file1.smt2 file2.smt2 file3.smt2
```

### 批量测试目录中的所有SMT文件

```bash
./smt_parser_comparison batch --dir path/to/benchmark/directory
```

## 外部依赖

为了使用所有解析器，您需要：

1. Python 3 和 pySMT库：`pip install pysmt`
2. Java JRE（用于ANTLR和jSMTLIB）
3. SWI-Prolog

外部解析器放置在项目根目录的`external`文件夹中，结构如下：

```
external/
  antlr/
    SMTLIBParser
  jsmtlib/
    jsmtlib.jar
  swipl/
    smtlib_parser.pl
```

## 结果报告

测试结果会显示在控制台，并保存在当前目录的`parser_benchmark_results.csv`文件中。

## 扩展支持

要添加新的解析器，您可以：

1. 在`src`目录中创建一个新的包装类，继承自`ParserInterface`
2. 在`ParserManager::initializeParsers()`方法中添加新解析器

## 许可

本项目采用MIT许可证开源。
