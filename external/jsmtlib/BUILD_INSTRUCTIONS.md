# jSMTLIB Java库编译和运行指南

## 项目概述

jSMTLIB是一个完整的Java SMT-LIB v2.x库，提供：
- SMT-LIB v2语法解析和打印
- 完整的AST（抽象语法树）表示
- 多种SMT求解器接口（Z3、CVC4等）
- 类型检查功能
- 脚本执行引擎
- 符号表管理

## 系统要求

1. **Java Development Kit (JDK)**: 8或更高版本
2. **建议使用Eclipse IDE**：项目最初为Eclipse项目设计
3. **可选**: Maven或Ant用于构建管理

## 项目结构

```
jSMTLIB-0.9.10.1/
├── SMT/                    # 主项目目录
│   ├── src/               # 源代码
│   │   ├── APIExample.java # API使用示例
│   │   └── org/smtlib/    # 主要包
│   │       ├── SMT.java   # 核心类
│   │       ├── IParser.java # 解析器接口
│   │       ├── ISolver.java # 求解器接口
│   │       └── ...        # 其他核心类
│   ├── test/              # 测试文件
│   ├── META-INF/          # 清单文件
│   └── .project           # Eclipse项目文件
├── SMTFeature/            # Eclipse特性
├── SMTPlugin/             # Eclipse插件
└── SMTUpdateSite/         # 更新站点
```

## 编译方法

### 方法1: 使用Eclipse IDE（推荐）

1. **启动Eclipse**
2. **导入项目**：
   - File → Import → Existing Projects into Workspace
   - 选择 `external/jsmtlib/jSMTLIB-0.9.10.1/SMT` 目录
   - 点击 Finish

3. **配置构建路径**：
   - 右键项目 → Properties → Java Build Path
   - 确保JRE版本兼容（建议Java 8+）

4. **构建项目**：
   - Project → Build Project
   - 或者启用自动构建：Project → Build Automatically

### 方法2: 命令行编译

#### 准备工作

```bash
# 进入项目目录
cd external/jsmtlib/jSMTLIB-0.9.10.1/SMT

# 创建构建目录
mkdir -p build/classes
mkdir -p build/lib
```

#### 编译源代码

```bash
# 编译所有Java文件
find src -name "*.java" | xargs javac -d build/classes -cp build/classes

# 或者分步编译
javac -d build/classes -cp build/classes src/org/smtlib/*.java
javac -d build/classes -cp build/classes src/org/smtlib/*/*.java
javac -d build/classes -cp build/classes src/APIExample.java
```

#### 创建JAR文件

```bash
# 创建库JAR
cd build/classes
jar cfm ../lib/jsmtlib.jar ../../META-INF/MANIFEST.MF org/
cd ../..

# 或者包含所有文件
jar cf build/lib/jsmtlib-complete.jar -C build/classes . -C src .
```

### 方法3: Maven构建（创建Maven项目）

创建 `pom.xml` 文件：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>org.smtlib</groupId>
    <artifactId>jsmtlib</artifactId>
    <version>0.9.10.1</version>
    <packaging>jar</packaging>

    <name>jSMTLIB</name>
    <description>Java SMT-LIB v2.x library</description>

    <properties>
        <maven.compiler.source>8</maven.compiler.source>
        <maven.compiler.target>8</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <sourceDirectory>src</sourceDirectory>
        <testSourceDirectory>test</testSourceDirectory>
        
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>8</source>
                    <target>8</target>
                </configuration>
            </plugin>
            
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>3.2.0</version>
                <configuration>
                    <archive>
                        <manifestFile>META-INF/MANIFEST.MF</manifestFile>
                    </archive>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

然后使用Maven编译：

```bash
# 创建pom.xml文件后
mvn clean compile
mvn package
```

## 运行示例

### 1. 运行API示例

```bash
# 方法1: 使用类路径
java -cp build/classes APIExample

# 方法2: 使用JAR文件
java -cp build/lib/jsmtlib.jar APIExample

# 方法3: 在Eclipse中直接运行
# 右键 APIExample.java → Run As → Java Application
```

### 2. 创建SMT-LIB解析器

创建一个简单的SMT-LIB解析器 `SMTParser.java`：

```java
import java.io.*;
import org.smtlib.*;
import org.smtlib.impl.Script;

public class SMTParser {
    
    public static void main(String[] args) {
        if (args.length != 1) {
            System.err.println("Usage: java SMTParser <smt2-file>");
            System.exit(1);
        }
        
        String filename = args[0];
        SMT smt = new SMT();
        
        try {
            // 读取文件
            FileReader fileReader = new FileReader(filename);
            ISource source = smt.smtConfig.smtFactory.createSource(
                new CharSequenceReader(fileReader), null);
            
            // 创建解析器
            IParser parser = smt.smtConfig.smtFactory.createParser(smt.smtConfig, source);
            
            // 解析所有命令
            Script script = new Script();
            while (!parser.isEOD()) {
                ICommand command = parser.parseCommand();
                if (command != null) {
                    script.commands().add(command);
                } else {
                    System.err.println("Parse error encountered");
                    break;
                }
            }
            
            // 输出结果
            IPrinter printer = smt.smtConfig.defaultPrinter;
            System.out.println("Successfully parsed " + script.commands().size() + " commands");
            
            // 打印所有命令
            for (ICommand cmd : script.commands()) {
                System.out.println(printer.toString(cmd));
            }
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
```

编译和运行：

```bash
# 编译
javac -cp build/classes SMTParser.java

# 运行
java -cp build/classes:. SMTParser example.smt2
```

### 3. 创建JSON输出解析器

创建 `SMTParserJSON.java` 以输出JSON格式：

```java
import java.io.*;
import java.util.*;
import org.smtlib.*;
import org.smtlib.impl.Script;

public class SMTParserJSON {
    
    public static void main(String[] args) {
        if (args.length != 1) {
            outputJSON(false, 0, 0, 0, Arrays.asList("Usage: java SMTParserJSON <smt2-file>"));
            return;
        }
        
        String filename = args[0];
        long startTime = System.currentTimeMillis();
        long startMemory = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory();
        
        SMT smt = new SMT();
        List<String> errors = new ArrayList<>();
        int nodeCount = 0;
        boolean success = false;
        
        try {
            // 读取文件
            FileReader fileReader = new FileReader(filename);
            ISource source = smt.smtConfig.smtFactory.createSource(
                new CharSequenceReader(fileReader), null);
            
            // 创建解析器
            IParser parser = smt.smtConfig.smtFactory.createParser(smt.smtConfig, source);
            
            // 解析所有命令
            Script script = new Script();
            while (!parser.isEOD()) {
                ICommand command = parser.parseCommand();
                if (command != null) {
                    script.commands().add(command);
                    nodeCount++;
                } else {
                    errors.add("Parse error encountered");
                    break;
                }
            }
            
            success = errors.isEmpty();
            
        } catch (Exception e) {
            errors.add("Error: " + e.getMessage());
        }
        
        long endTime = System.currentTimeMillis();
        long endMemory = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory();
        
        double parseTime = (endTime - startTime) / 1000.0;
        long memoryUsage = Math.max(0, endMemory - startMemory);
        
        outputJSON(success, parseTime, memoryUsage, nodeCount, errors);
    }
    
    private static void outputJSON(boolean success, double parseTime, long memoryUsage, 
                                  int nodeCount, List<String> errors) {
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"success\":").append(success).append(",");
        json.append("\"parse_time\":").append(parseTime).append(",");
        json.append("\"memory_usage\":").append(memoryUsage).append(",");
        json.append("\"ast_node_count\":").append(nodeCount).append(",");
        json.append("\"errors\":[");
        
        for (int i = 0; i < errors.size(); i++) {
            if (i > 0) json.append(",");
            json.append("\"").append(errors.get(i).replace("\"", "\\\"")).append("\"");
        }
        
        json.append("]}");
        System.out.println(json.toString());
    }
}
```

## 集成到比较项目

### 1. 创建包装脚本

创建 `jsmtlib_wrapper.sh`：

```bash
#!/bin/bash

JAVA_PARSER="java -cp build/classes:. SMTParserJSON"
INPUT_FILE="$1"

if [ ! -f "$INPUT_FILE" ]; then
    echo '{"success": false, "parse_time": 0, "memory_usage": 0, "ast_node_count": 0, "errors": ["Input file not found"]}'
    exit 1
fi

# 运行Java解析器
timeout 30 $JAVA_PARSER "$INPUT_FILE"
```

### 2. 在C++项目中集成

在 `parser.cpp` 中添加jSMTLIB解析器：

```cpp
class JSMTLIBParser : public ParserInterface {
private:
    std::string wrapper_path;
    std::string java_classpath;

public:
    JSMTLIBParser(const std::string& path = "./jsmtlib_wrapper.sh") 
        : wrapper_path(path) {}

    ParseResult parse(const std::string& filename) override {
        ParseResult result;
        
        try {
            std::string cmd = wrapper_path + " \"" + filename + "\"";
            std::string output = exec(cmd);
            
            // 解析JSON输出
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            
            result.success = json["success"].getBool();
            result.parse_time = json["parse_time"].getNumber();
            result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
            result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
            
            if (json["errors"].isArray()) {
                const auto& errors = json["errors"].getArray();
                for (const auto& err : errors) {
                    result.errors.push_back(err.getString());
                }
            }
        } catch (const std::exception& e) {
            result.success = false;
            result.errors.push_back(std::string("jSMTLIB parser error: ") + e.what());
        }
        
        return result;
    }
};
```

## 高级功能

### 1. 使用求解器接口

```java
import org.smtlib.solvers.Solver_z3_4_3;

// 创建Z3求解器实例
ISolver solver = new Solver_z3_4_3(smt.smtConfig, "/path/to/z3");
solver.start();

// 执行SMT命令
solver.set_logic("QF_LIA", null);
solver.declare_fun(/* ... */);
solver.assertExpr(/* ... */);
IResponse response = solver.check_sat();

System.out.println(response.isSuccess());
```

### 2. 类型检查

```java
import org.smtlib.TypeChecker;

TypeChecker checker = new TypeChecker(smt.smtConfig);
IResponse response = checker.check(script);
if (!response.isSuccess()) {
    System.err.println("Type checking failed: " + response.toString());
}
```

### 3. 自定义解析器

```java
// 自定义解析器配置
IParser.ParserConfig config = new IParser.ParserConfig();
config.setStrictMode(true);
config.setErrorTolerant(false);

IParser parser = smt.smtConfig.smtFactory.createParser(config, source);
```

## 测试

### 1. 运行内置测试

```bash
# 如果有JUnit测试
java -cp build/classes:junit-4.13.2.jar org.junit.runner.JUnitCore TestClassName
```

### 2. 解析测试

```bash
# 测试简单的SMT-LIB文件
echo "(set-logic QF_LIA)" > test.smt2
echo "(check-sat)" >> test.smt2
echo "(exit)" >> test.smt2

java -cp build/classes:. SMTParser test.smt2
```

## 性能优化

### 1. JVM参数调优

```bash
# 增加堆内存
java -Xmx2G -cp build/classes:. SMTParser large_file.smt2

# 使用G1垃圾收集器
java -XX:+UseG1GC -cp build/classes:. SMTParser large_file.smt2
```

### 2. 并行处理

```java
// 使用并行流处理多个文件
List<String> files = Arrays.asList("file1.smt2", "file2.smt2", "file3.smt2");
files.parallelStream().forEach(file -> {
    // 解析每个文件
});
```

## 常见问题解决

### 1. 内存不足

```bash
# 增加JVM堆内存
java -Xmx4G -cp build/classes:. SMTParser large_file.smt2
```

### 2. 编译错误

```bash
# 检查Java版本
java -version
javac -version

# 清理并重新编译
rm -rf build/classes/*
find src -name "*.java" | xargs javac -d build/classes
```

### 3. 找不到类

```bash
# 检查类路径
java -cp build/classes:. -verbose:class SMTParser test.smt2
```

## 参考资源

- [jSMTLIB官方文档](https://github.com/SMTLIBv2/jSMTLIB)
- [SMT-LIB v2.x标准](http://smtlib.cs.uiowa.edu/)
- [Eclipse IDE](https://www.eclipse.org/)
- [Maven构建工具](https://maven.apache.org/)

## 输出格式

JSON输出格式符合项目要求：

```json
{
  "success": true,
  "parse_time": 0.123,
  "memory_usage": 1024,
  "ast_node_count": 42,
  "errors": []
}
``` 