#pragma once

#include <string>
#include <iostream>
#include <vector>
#include <memory>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <array>
#include <functional>
#include <stdexcept>
#include <algorithm>
#include <filesystem>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include "simple_json.h"

// 添加缺少的头文件
#ifdef _WIN32
#include <io.h>
#define F_OK 0
#define access _access
#else
#include <unistd.h>
#endif

namespace SMTComparison {

// 全局超时设置（秒）
extern int g_timeout_seconds;

// 安全执行解析函数，防止段错误导致程序中断
// 返回值: true表示解析成功，false表示解析失败或发生段错误
bool safeExecute(std::function<bool()> parseFunc, int timeoutSeconds = 30);

// 写入管道的消息类型
enum MessageType {
    MSG_SUCCESS = 0,
    MSG_FAILURE = 1,
    MSG_CRASH = 2
};

// ======== 性能指标测量工具 ========
class PerformanceMetrics {
public:
    // 测量函数执行时间(毫秒)
    static double measureExecutionTime(const std::function<void()>& func) {
        auto start = std::chrono::high_resolution_clock::now();
        func();
        auto end = std::chrono::high_resolution_clock::now();
        
        std::chrono::duration<double, std::milli> duration = end - start;
        return duration.count();
    }
    
    // 获取当前进程的内存使用量(KB)
    static size_t getCurrentMemoryUsage() {
#ifdef _WIN32
        // Windows实现
        return 0; // 需要实现Windows下的内存使用统计
#else
        // Linux/Unix实现 - 从/proc/self/status读取
        std::ifstream status("/proc/self/status");
        std::string line;
        while (std::getline(status, line)) {
            if (line.find("VmRSS:") != std::string::npos) {
                std::istringstream iss(line);
                std::string label;
                size_t usage;
                std::string unit;
                iss >> label >> usage >> unit;
                return usage; // 返回KB为单位的内存使用量
            }
        }
        return 0; // 如果无法获取信息
#endif
    }
    
    // 返回文件大小(字节)
    static size_t getFileSize(const std::string& filename) {
        std::ifstream file(filename, std::ifstream::ate | std::ifstream::binary);
        // 修复类型不匹配问题
        if (file.good()) {
            auto pos = file.tellg();
            return static_cast<size_t>(pos);
        }
        return 0;
    }
};

// ======== 解析结果信息 ========
struct ParseResult {
    bool success;                  // 解析是否成功
    double parse_time;             // 解析时间(ms)
    size_t memory_usage;           // 内存使用量(KB)
    size_t ast_node_count;         // AST节点数量
    std::vector<std::string> errors; // 错误信息

    ParseResult() : success(false), parse_time(0), memory_usage(0),
                   ast_node_count(0) {}
};

// ======== 解析器接口 ========
class ParserInterface {
public:
    virtual ~ParserInterface() = default;
    
    // 解析文件并返回结果
    virtual ParseResult parse(const std::string& filename) = 0;
    
    // 解析器名称
    virtual std::string getName() const = 0;
    
    // 解析器版本
    virtual std::string getVersion() const = 0;
    
    // 解析器语言
    virtual std::string getLanguage() const = 0;
    
    // 解析器支持的功能
    virtual std::vector<std::string> getFeatures() const = 0;

protected:
    // 使用子进程安全地解析文件
    bool safeParseFile(const std::function<bool()>& parseFunc);
};

// ======== 原生解析器实现 ========
class NativeParser : public ParserInterface {
public:
    NativeParser();
    
    ParseResult parse(const std::string& filename) override;
    
    std::string getName() const override {
        return "native";
    }
    
    std::string getVersion() const override {
        return "1.0";
    }
    
    std::string getLanguage() const override {
        return "C++";
    }
    
    std::vector<std::string> getFeatures() const override {
        return {"SMT-LIB 2.6", "基本语法检查"};
    }
};

// ======== 外部解析器 ========
class ExternalParser : public ParserInterface {
protected:
    std::string parser_path;
    std::string parser_name;
    std::string parser_version;
    std::string parser_language;
    std::vector<std::string> parser_features;
    
    // 执行shell命令并返回结果（带超时功能）
    std::string exec(const std::string& cmd, int timeout_seconds = -1) {
        // 如果没有指定超时时间，使用全局设置
        if (timeout_seconds == -1) {
            timeout_seconds = g_timeout_seconds;
        }
        // 使用timeout命令包装原始命令
        std::string timeout_cmd = "timeout " + std::to_string(timeout_seconds) + " " + cmd;
        
        std::array<char, 128> buffer;
        std::string result;
        FILE* pipe = popen(timeout_cmd.c_str(), "r");
        if (!pipe) {
            throw std::runtime_error("popen() failed!");
        }
        
        while (fgets(buffer.data(), buffer.size(), pipe) != nullptr) {
            result += buffer.data();
        }
        
        // 检查退出状态
        int exit_code = pclose(pipe);
        if (WEXITSTATUS(exit_code) == 124) { // timeout命令在超时时返回124
            throw std::runtime_error("命令执行超时 (" + std::to_string(timeout_seconds) + " 秒)");
        }
        
        return result;
    }

public:
    ExternalParser(
        const std::string& path, 
        const std::string& name, 
        const std::string& version, 
        const std::string& language,
        const std::vector<std::string>& features
    ) : parser_path(path), parser_name(name), parser_version(version),
        parser_language(language), parser_features(features) {
        
        // 检查解析器是否存在或可执行
        if (!path.empty() && access(parser_path.c_str(), F_OK) != 0) {
            std::cerr << "警告: 无法访问解析器: " << parser_path << std::endl;
        }
    }
    
    std::string getName() const override {
        return parser_name;
    }
    
    std::string getVersion() const override {
        return parser_version;
    }
    
    std::string getLanguage() const override {
        return parser_language;
    }
    
    std::vector<std::string> getFeatures() const override {
        return parser_features;
    }
};

// ======== pySMT解析器实现 ========
class PySMTParser : public ExternalParser {
private:
    std::string python_path;
    
    // 查找可用的Python路径
    std::string findPythonPath() {
        std::vector<std::string> candidates = {
            "/home/fuqi/anaconda3/envs/smt/bin/python",  // 您的conda环境
            "/home/fuqi/anaconda3/bin/python",           // anaconda base环境
            "python3",                                   // 系统python3
            "python"                                     // 系统python
        };
        
        for (const auto& candidate : candidates) {
            try {
                std::string check_cmd = candidate + " -c \"import pysmt; print('OK')\" 2>/dev/null";
                std::string result = exec(check_cmd);
                if (result.find("OK") != std::string::npos) {
                    return candidate;
                }
            } catch (...) {
                continue;
            }
        }
        
        // 如果都不行，返回默认值
        return "python3";
    }
    
public:
    PySMTParser(const std::string& python = "") : 
        ExternalParser(
            "", 
            "pysmt", 
            "", 
            "Python", 
            {"SMT-LIB 2.6", "多种理论支持", "与多种求解器集成"}
        ),
        python_path(python.empty() ? findPythonPath() : python) {
        
        // 检查pySMT是否可用
        try {
            std::string check_cmd = python_path + " -c \"import pysmt; print('pySMT available')\"";
            std::string result = exec(check_cmd);
            if (result.find("pySMT available") == std::string::npos) {
                throw std::runtime_error("pySMT not available with " + python_path);
            }
            
            // 获取版本
            std::string version_cmd = python_path + " -c \"import pysmt; print(pysmt.__version__)\"";
            parser_version = exec(version_cmd);
            if (!parser_version.empty() && parser_version[parser_version.length()-1] == '\n') {
                parser_version.pop_back(); // 删除末尾换行符
            }
        } catch (const std::exception& e) {
            throw std::runtime_error("pySMT not available: " + std::string(e.what()));
        }
    }
    
    ParseResult parse(const std::string& filename) override;
};



// ======== jSMTLIB解析器实现 ========
class JSMTLIBParser : public ExternalParser {
public:
    JSMTLIBParser(const std::string& jsmtlib_dir = "external/jsmtlib") 
        : ExternalParser(
            jsmtlib_dir, 
            "jsmtlib", 
            "0.9.10.1", 
            "Java", 
            {"SMT-LIB 2.6", "AST节点计数", "Java解析器"}
        ) {}
    
    ParseResult parse(const std::string& filename) override;
};

// ======== Z3解析器实现 ========
class Z3Parser : public ExternalParser {
public:
    Z3Parser(const std::string& path = "external/z3/z3_parser") 
        : ExternalParser(
            path, 
            "z3", 
            "4.15.2", 
            "C++", 
            {"SMT-LIB 2.6", "C++ Z3 API", "AST节点计数"}
        ) {}
    
    ParseResult parse(const std::string& filename) override;
};

// ======== ANTLR4解析器实现 ========
class ANTLR4Parser : public ExternalParser {
public:
    ANTLR4Parser(const std::string& antlr4_dir = "external/antlr4_parser") 
        : ExternalParser(
            antlr4_dir, 
            "antlr4", 
            "4.13.1", 
            "Java", 
            {"SMT-LIB 2.6", "ANTLR4语法", "AST节点计数", "Java实现"}
        ) {}
    
    ParseResult parse(const std::string& filename) override;
};





// ======== 解析器管理器 ========
class ParserManager {
private:
    std::vector<std::shared_ptr<ParserInterface>> parsers;
    
public:
    // 添加解析器
    void addParser(std::shared_ptr<ParserInterface> parser) {
        parsers.push_back(parser);
    }
    
    // 初始化所有支持的解析器
    bool initializeParsers();
    
    // 测试单个文件的性能
    std::vector<ParseResult> testFile(const std::string& filename);
    
    // 测试多个文件的性能
    void benchmarkFiles(const std::vector<std::string>& filenames);
    void benchmarkFiles(const std::vector<std::string>& filenames, const std::string& outputFilename);
    
    // 生成性能对比报告
    void generateReport(
        const std::vector<std::string>& filenames,
        const std::vector<std::vector<ParseResult>>& all_results
    );
    void generateReport(
        const std::vector<std::string>& filenames,
        const std::vector<std::vector<ParseResult>>& all_results,
        const std::string& outputFilename
    );
    
    // 获取已加载的解析器数量
    size_t getParserCount() const {
        return parsers.size();
    }
    
    // 列出所有可用的解析器
    void listParsers() const;
    
    // 获取所有解析器名称
    std::vector<std::string> getParserNames() const;
    
    // 通过名称获取解析器
    std::shared_ptr<ParserInterface> getParserByName(const std::string& name) const;
    
    // 测试特定解析器的性能
    ParseResult testFileWithParser(const std::string& filename, const std::string& parserName);
    
    // 对特定解析器进行基准测试
    void benchmarkFilesWithParser(const std::vector<std::string>& filenames, const std::string& parserName);
    void benchmarkFilesWithParser(const std::vector<std::string>& filenames, const std::string& parserName, const std::string& outputFilename);
    
    // 生成单个解析器的报告
    void generateSingleParserReport(
        const std::string& parserName,
        const std::vector<std::string>& filenames,
        const std::vector<ParseResult>& results
    );
    void generateSingleParserReport(
        const std::string& parserName,
        const std::vector<std::string>& filenames,
        const std::vector<ParseResult>& results,
        const std::string& outputFilename
    );
};

} // namespace SMTComparison 