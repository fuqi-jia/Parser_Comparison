# 失败记录收集工具使用示例

## 脚本功能

`collect_failure.py` 是一个用于从指定文件夹收集失败记录的工具，支持两种模式：

1. **精确匹配模式**：查找以"失败"结尾的行
2. **模式匹配模式**：查找包含失败关键词的行（如：失败、ERROR、FAIL等）

## 使用方法

### 1. 命令行使用

#### 基本用法（精确匹配）
```bash
# 收集指定目录中以"失败"结尾的行
python3 collect_failure.py /path/to/directory

# 指定输出文件名
python3 collect_failure.py /path/to/directory -o my_failures.txt

# 指定要搜索的文件类型
python3 collect_failure.py /path/to/directory -e .txt .log .out
```

#### 模式匹配模式
```bash
# 使用默认失败模式（失败、ERROR、FAIL等）
python3 collect_failure.py /path/to/directory -p

# 自定义搜索模式
python3 collect_failure.py /path/to/directory -p --patterns "失败" "错误" "FAILED" "ERROR"
```

### 2. 交互式使用

直接运行脚本，按提示输入参数：
```bash
python3 collect_failure.py
```

## 示例演示

### 测试数据

我们已经创建了测试数据在 `test_data/` 目录中：

- `log1.txt`: 包含系统日志，有3行以"失败"结尾
- `error.log`: 包含错误日志，有3行以"失败"结尾  
- `result.out`: 包含测试结果，有4行以"失败"结尾

### 运行示例

#### 示例1：精确匹配（以"失败"结尾）

```bash
cd results
python3 collect_failure.py test_data -o exact_failures.txt
```

输出示例：
```
文件失败记录收集工具
==================================================
开始扫描目录: test_data
搜索文件类型: ['.txt', '.log', '.out', '.err', '.result']
--------------------------------------------------
发现失败: log1.txt:3 - 2024-01-15 10:30:20 - 数据库连接失败
发现失败: log1.txt:7 - 2024-01-15 10:35:10 - 用户认证失败
发现失败: log1.txt:8 - 2024-01-15 10:36:00 - 文件上传操作失败
发现失败: error.log:1 - [ERROR] 2024-01-15 11:00:01 - 内存分配失败
发现失败: error.log:4 - [ERROR] 2024-01-15 11:00:15 - 网络请求超时失败
发现失败: error.log:6 - [ERROR] 2024-01-15 11:00:25 - 解析配置文件失败
发现失败: result.out:3 - 测试案例 003: 语法检查失败
发现失败: result.out:5 - 测试案例 005: 编译失败
发现失败: result.out:6 - 测试案例 006: 运行时错误失败
发现失败: result.out:8 - 测试案例 008: 内存泄漏检测失败

报告已生成: exact_failures.txt
共发现 10 个失败记录

✓ 收集完成
```

#### 示例2：模式匹配（包含失败关键词）

```bash
python3 collect_failure.py test_data -p -o pattern_failures.txt
```

### 生成的报告格式

报告文件包含以下内容：

```
============================================================
失败记录收集报告
============================================================
生成时间: 2024-01-15 15:30:00
扫描目录: test_data
处理文件数: 3
总行数: 23
失败记录数: 10
============================================================

失败记录详情:
------------------------------------------------------------
[001] 文件: log1.txt
      行号: 3
      内容: 2024-01-15 10:30:20 - 数据库连接失败
      路径: /full/path/to/test_data/log1.txt
------------------------------------------------------------
[002] 文件: log1.txt
      行号: 7
      内容: 2024-01-15 10:35:10 - 用户认证失败
      路径: /full/path/to/test_data/log1.txt
------------------------------------------------------------
...

按文件统计:
------------------------------------------------------------
error.log: 3 个失败
log1.txt: 3 个失败
result.out: 4 个失败

报告生成完成。
```

## 命令行参数详解

```
usage: collect_failure.py [-h] [-o OUTPUT] [-e [EXTENSIONS ...]] [-p] [--patterns [PATTERNS ...]] directory

从指定文件夹收集以"失败"结尾的行

positional arguments:
  directory             要搜索的目录路径

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        输出文件名 (默认: failure_report.txt)
  -e [EXTENSIONS ...], --extensions [EXTENSIONS ...]
                        要搜索的文件扩展名 (默认: .txt .log .out .err .result)
  -p, --pattern-mode    使用模式匹配模式（搜索失败、ERROR等关键词）
  --patterns [PATTERNS ...]
                        在模式模式下要搜索的模式列表
```

## 高级用法

### 1. 只搜索特定类型文件
```bash
# 只搜索.log文件
python3 collect_failure.py /var/log -e .log

# 搜索多种类型
python3 collect_failure.py /path/to/logs -e .txt .log .err .out
```

### 2. 自定义失败模式
```bash
# 搜索包含中英文错误关键词的行
python3 collect_failure.py logs/ -p --patterns "失败" "错误" "异常" "ERROR" "FAILED" "EXCEPTION"

# 搜索特定的错误类型
python3 collect_failure.py logs/ -p --patterns "超时" "内存不足" "网络错误"
```

### 3. 输出到不同位置
```bash
# 输出到指定目录
python3 collect_failure.py logs/ -o /reports/daily_failures.txt

# 使用时间戳命名
python3 collect_failure.py logs/ -o "failures_$(date +%Y%m%d_%H%M%S).txt"
```

## 注意事项

1. **文件编码**：脚本自动处理UTF-8编码，对于其他编码会忽略错误字符
2. **大文件处理**：对于很大的文件，处理可能需要一些时间
3. **权限问题**：确保对目标目录有读取权限
4. **递归搜索**：脚本会递归搜索所有子目录
5. **空行处理**：自动忽略空行和只包含空白字符的行

## 实际应用场景

- **日志分析**：从系统日志中快速定位错误信息
- **测试报告**：收集测试失败的案例
- **构建日志**：分析编译或部署过程中的失败
- **监控数据**：从监控日志中提取告警信息
- **故障排查**：快速汇总各种日志文件中的错误信息 