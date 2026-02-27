#include "smt_parser_comparison.h"
#include "simple_json.h"
#include "process_runner.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <random>
#include <filesystem>

namespace SMTComparison {

// 全局超时设置（秒）
int g_timeout_seconds = 60;

// 执行外部命令并获取输出的帮助函数（带超时功能）
std::string exec(const std::string& cmd, int timeout_seconds = -1) {
    // 如果没有指定超时时间，使用全局设置
    if (timeout_seconds == -1) {
        timeout_seconds = g_timeout_seconds;
    }
    // 使用timeout命令包装原始命令
    std::string timeout_cmd = "timeout " + std::to_string(timeout_seconds) + " " + cmd;
    
    std::array<char, 4096> buffer;
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

// 使用 ProcessRunner 执行命令，返回完整结果（含 peak_rss、stderr、exit_code）
static ProcessRunResult runExternalCommand(const std::string& cmd) {
    return ProcessRunner::run(cmd, g_timeout_seconds);
}

// 解析 external 下 parser 的路径：从项目根目录查找（支持从 build/ 运行）
static std::string resolveExternalPath(const std::string& path) {
    namespace fs = std::filesystem;
    fs::path p(path);
    if (p.is_absolute() && fs::exists(p))
        return p.string();
    fs::path base;
    // 1) 当前目录
    base = fs::current_path();
    if (fs::exists(base / p)) return (base / p).string();
    // 2) 上一级（例如从 build/ 运行）
    base = fs::current_path().parent_path();
    if (fs::exists(base / p)) return (base / p).string();
#ifdef __linux__
    // 3) 从可执行文件路径向上找包含 external 的目录
    char buf[4096];
    ssize_t n = readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    if (n > 0) {
        buf[n] = '\0';
        fs::path exe_dir = fs::path(buf).parent_path();
        for (int i = 0; i < 5; ++i) {
            if (exe_dir.empty() || !fs::exists(exe_dir)) break;
            if (fs::exists(exe_dir / "external")) {
                base = exe_dir;
                if (fs::exists(base / p)) return (base / p).string();
                break;
            }
            exe_dir = exe_dir.parent_path();
        }
    }
#endif
    return path;
}

static ResultCode resultCodeFromStderr(const std::string& stderr_out) {
    std::string lower;
    lower.reserve(stderr_out.size());
    for (char c : stderr_out) lower.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    if (lower.find("unsupported") != std::string::npos || lower.find("not supported") != std::string::npos)
        return ResultCode::UNSUPPORTED;
    if (lower.find("type") != std::string::npos || lower.find("sort") != std::string::npos)
        return ResultCode::TYPE_ERROR;
    if (lower.find("parse error") != std::string::npos || lower.find("syntax") != std::string::npos)
        return ResultCode::PARSE_ERROR;
    if (lower.find("out of memory") != std::string::npos || lower.find("oom") != std::string::npos)
        return ResultCode::OOM;
    return ResultCode::UNKNOWN;
}

static void fillResultFromProcessRun(ParseResult& result, const ProcessRunResult& pr, bool json_success) {
    result.parse_time = pr.wall_time_ms;
    result.peak_rss_kb = pr.peak_rss_kb;
    result.exit_code = pr.exit_code;
    result.stderr_snippet = pr.stderr_output;
    if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
    if (pr.timed_out) {
        result.result_code = ResultCode::TIMEOUT;
        result.success = false;
        if (result.errors.empty()) result.errors.push_back("命令执行超时");
    } else if (pr.exit_code != 0 && pr.term_signal != 0) {
        result.result_code = ResultCode::CRASH;
        result.success = false;
    } else if (pr.exit_code != 0) {
        result.result_code = resultCodeFromStderr(pr.stderr_output);
        result.success = false;
    } else {
        result.result_code = json_success ? ResultCode::OK : ResultCode::PARSE_ERROR;
        result.success = json_success;
    }
}

// ======== NativeParser 实现 ========
NativeParser::NativeParser() {
    // 不需要初始化
}

ParseResult NativeParser::parse(const std::string& filename) {
    ParseResult result;
    
    try {
        // 获取wrapper的绝对路径
        std::filesystem::path current_path = std::filesystem::current_path();
        std::string wrapper_path;
        
        // 尝试多个可能的位置
        std::vector<std::string> possible_paths = {
            (current_path / "smt_parser_wrapper").string(),
            (current_path / "build" / "smt_parser_wrapper").string(),
            (current_path / ".." / "build" / "smt_parser_wrapper").string(),
            (std::filesystem::absolute("smt_parser_wrapper")).string(),
            (std::filesystem::absolute("build/smt_parser_wrapper")).string(),
            (std::filesystem::absolute("../build/smt_parser_wrapper")).string()
        };
        
        for (const auto& path : possible_paths) {
            if (std::filesystem::exists(path)) {
                wrapper_path = path;
                break;
            }
        }
        
        if (wrapper_path.empty()) {
            throw std::runtime_error("无法找到smt_parser_wrapper可执行文件");
        }
        
        std::cout << "使用wrapper路径: " << wrapper_path << std::endl;
        
        // 构建调用wrapper的命令
        std::string cmd = wrapper_path + " \"" + filename + "\"";
        
        ProcessRunResult pr = runExternalCommand(cmd);
        std::string output = pr.stdout_output;
        result.parse_time = pr.wall_time_ms;
        result.peak_rss_kb = pr.peak_rss_kb;
        result.exit_code = pr.exit_code;
        result.stderr_snippet = pr.stderr_output;
        if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
        if (pr.timed_out) {
            result.success = false;
            result.result_code = ResultCode::TIMEOUT;
            result.errors.push_back("命令执行超时");
            return result;
        }
        
        // 解析JSON输出
        try {
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            
            // 填充结果结构
            result.success = json["success"].getBool();
            result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
            // 只使用wrapper报告的解析时间
            result.parse_time = json["parse_time"].getNumber();
            result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
            result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
            
            // 获取错误信息
            if (json["errors"].isArray()) {
                const auto& errors = json["errors"].getArray();
                for (const auto& err : errors) {
                    result.errors.push_back(err.getString());
                }
            }
        } catch (const std::exception& e) {
            result.success = false;
            result.result_code = ResultCode::PARSE_ERROR;
            result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
            result.errors.push_back("原始输出: " + output);
        }
    } catch (const std::exception& e) {
        result.success = false;
        result.result_code = ResultCode::CRASH;
        result.errors.push_back(std::string("执行外部解析器失败: ") + e.what());
    }
    
    return result;
}

// ======== PySMTParser 实现 ========
ParseResult PySMTParser::parse(const std::string& filename) {
    ParseResult result;
    
    try {
        // 获取pySMT解析器脚本的路径
        std::filesystem::path current_path = std::filesystem::current_path();
        std::string script_path;
        
        // 尝试多个可能的位置
        std::vector<std::string> possible_paths = {
            (current_path / "external" / "pysmt" / "pysmt_parser.py").string(),
            (current_path / ".." / "external" / "pysmt" / "pysmt_parser.py").string(),
            (std::filesystem::absolute("external/pysmt/pysmt_parser.py")).string(),
            (std::filesystem::absolute("../external/pysmt/pysmt_parser.py")).string()
        };
        
        for (const auto& path : possible_paths) {
            if (std::filesystem::exists(path)) {
                script_path = path;
                break;
            }
        }
        
        if (script_path.empty()) {
            throw std::runtime_error("无法找到pysmt_parser.py脚本");
        }
        
        // 构建Python命令
        std::string cmd = python_path + " \"" + script_path + "\" \"" + filename + "\"";
        
        ProcessRunResult pr = runExternalCommand(cmd);
        std::string output = pr.stdout_output;
        result.peak_rss_kb = pr.peak_rss_kb;
        result.exit_code = pr.exit_code;
        result.stderr_snippet = pr.stderr_output;
        result.parse_time = pr.wall_time_ms;
        if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
        if (pr.timed_out) {
            result.success = false;
            result.result_code = ResultCode::TIMEOUT;
            result.errors.push_back("命令执行超时");
            return result;
        }
        if (pr.exit_code != 0) {
            result.result_code = resultCodeFromStderr(pr.stderr_output);
            result.success = false;
        }
        
        // 检查输出是否为空
        if (output.empty()) {
            result.success = false;
            result.errors.push_back("Python脚本没有输出");
            result.errors.push_back("执行的命令: " + cmd);
            return result;
        }
        
        // 解析JSON输出
        try {
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            
            // 填充结果结构
            result.success = json["success"].getBool();
            result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
            result.parse_time = json["parse_time"].getNumber();
            result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
            result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
            
            // 获取错误信息
            if (json["errors"].isArray()) {
                const auto& errors = json["errors"].getArray();
                for (const auto& err : errors) {
                    result.errors.push_back(err.getString());
                }
            }
        } catch (const std::exception& e) {
            result.success = false;
            result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
            result.errors.push_back("原始输出: " + output);
            result.errors.push_back("执行的命令: " + cmd);
            
            // 尝试查找是否有常见的错误模式
            if (output.find("list index out of range") != std::string::npos) {
                result.errors.push_back("检测到list index out of range错误，这可能是由于参数传递或环境问题引起的");
            }
            if (output.find("ImportError") != std::string::npos) {
                result.errors.push_back("检测到ImportError，请检查pySMT是否正确安装");
            }
        }
        
        } catch (const std::exception& e) {
        result.success = false;
        result.result_code = ResultCode::CRASH;
        result.errors.push_back(std::string("执行pySMT解析器失败: ") + e.what());
    }
    
    return result;
}



// ======== JSMTLIBParser 实现 ========
ParseResult JSMTLIBParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 构建调用Java解析器的命令
    // 使用绝对路径构建classpath，避免cd命令
    std::filesystem::path abs_jsmtlib_path(resolveExternalPath(parser_path));
    std::filesystem::path abs_filename_path = std::filesystem::absolute(filename);
    
    std::string jsmtlib_src = abs_jsmtlib_path.string() + "/jSMTLIB-0.9.10.1/SMT/src";
    std::string classpath = "\"" + jsmtlib_src + ":" + abs_jsmtlib_path.string() + "\"";
    std::string cmd = "java -cp " + classpath + " jsmtlib_parser \"" + abs_filename_path.string() + "\"";
    
    ProcessRunResult pr = runExternalCommand(cmd);
    std::string output = pr.stdout_output;
    result.parse_time = pr.wall_time_ms;
    result.peak_rss_kb = pr.peak_rss_kb;
    result.exit_code = pr.exit_code;
    result.stderr_snippet = pr.stderr_output;
    if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
    if (pr.timed_out) {
        result.success = false;
        result.result_code = ResultCode::TIMEOUT;
        result.errors.push_back("命令执行超时");
        return result;
    }
    if (pr.exit_code != 0) {
        result.success = false;
        result.result_code = resultCodeFromStderr(pr.stderr_output);
    }
    
    try {
        SimpleJson::Value json = SimpleJson::Parser::parse(output);
        
        // 填充结果结构
        result.success = json["success"].getBool();
        result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
        result.parse_time = json["parse_time"].getNumber();
        result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
        result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
        
        // 获取错误信息
        if (json["errors"].isArray()) {
            const auto& errors = json["errors"].getArray();
            for (const auto& err : errors) {
                result.errors.push_back(err.getString());
            }
        }
        // parsing_method 为元数据，不放入 errors，避免成功时误显示为“错误信息”
        
    } catch (const std::exception& e) {
        result.success = false;
        result.result_code = ResultCode::PARSE_ERROR;
        result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
        result.errors.push_back("原始输出: " + output);
    }
    
    return result;
}

// ======== ParserManager 实现 ========
bool ParserManager::initializeParsers() {
    try {
        // 添加本地解析器
        addParser(std::make_shared<NativeParser>());
        
        // 尝试添加pySMT解析器
        try {
            addParser(std::make_shared<PySMTParser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化pySMT解析器: " << e.what() << std::endl;
        }
        

        
        // 尝试添加jSMTLIB解析器
        try {
            addParser(std::make_shared<JSMTLIBParser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化jSMTLIB解析器: " << e.what() << std::endl;
        }
        
        // 尝试添加Z3解析器
        try {
            addParser(std::make_shared<Z3Parser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化Z3解析器: " << e.what() << std::endl;
        }
        
        // 尝试添加ANTLR4解析器
        try {
            addParser(std::make_shared<ANTLR4Parser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化ANTLR4解析器: " << e.what() << std::endl;
        }
        
        // 尝试添加 cvc5 解析器
        try {
            addParser(std::make_shared<Cvc5Parser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化 cvc5 解析器: " << e.what() << std::endl;
        }
        
        // 尝试添加 smt-switch 解析器
        try {
            addParser(std::make_shared<SmtSwitchParser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化 smt-switch 解析器: " << e.what() << std::endl;
        }

        
        return !parsers.empty();
    } catch (const std::exception& e) {
        std::cerr << "初始化解析器时出错: " << e.what() << std::endl;
        return false;
    }
}

std::vector<ParseResult> ParserManager::testFile(const std::string& filename) {
    std::vector<ParseResult> results;
    
    for (const auto& parser : parsers) {
        try {
            std::string abs_filename = std::filesystem::absolute(filename).string();
            std::cout << "使用 " << parser->getName() << " 解析 " << abs_filename << " (超时: " << g_timeout_seconds << "秒)" << std::endl;
            
            ParseResult result = parser->parse(filename);
            
            std::cout << "  解析状态: " << (result.success ? "成功" : "失败") << std::endl;
            std::cout << "  解析时间: " << result.parse_time << " ms" << std::endl;
            std::cout << "  内存使用: " << result.memory_usage << " KB" << std::endl;
            std::cout << "  AST节点数: " << result.ast_node_count;
            if (parser->getName() == "antlr4")
                std::cout << " (parse tree 节点，与其他 parser 的语义 AST 口径不同)";
            std::cout << std::endl;
            
            if (!result.errors.empty()) {
                std::cout << "  错误信息:" << std::endl;
                for (const auto& err : result.errors) {
                    std::cout << "    " << err << std::endl;
                }
            }
            
            results.push_back(result);
        } catch (const std::exception& e) {
            std::cerr << "  测试过程中出错: " << e.what() << std::endl;
            
            ParseResult errorResult;
            errorResult.success = false;
            errorResult.errors.push_back(e.what());
            results.push_back(errorResult);
        }
    }
    
    return results;
}

void ParserManager::benchmarkFiles(const std::vector<std::string>& filenames) {
    // 准备结果矩阵
    std::vector<std::vector<ParseResult>> all_results;
    
    for (const auto& filename : filenames) {
        std::vector<ParseResult> file_results = testFile(filename);
        all_results.push_back(file_results);
    }
    
    // 生成对比报告
    generateReport(filenames, all_results);
}

void ParserManager::generateReport(
    const std::vector<std::string>& filenames,
    const std::vector<std::vector<ParseResult>>& all_results
) {
    // 输出到控制台
    std::cout << "\n========== SMT解析器性能对比报告 ==========\n" << std::endl;
    
    // 计算平均值
    for (size_t p = 0; p < parsers.size(); p++) {
        double avg_time = 0;
        size_t avg_memory = 0;
        size_t avg_nodes = 0;
        size_t success_count = 0;
        
        std::cout << parsers[p]->getName() << " (" << parsers[p]->getLanguage() << "):" << std::endl;
        
        for (size_t f = 0; f < filenames.size(); f++) {
            if (f < all_results.size() && p < all_results[f].size()) {
                const auto& result = all_results[f][p];
                
                if (result.success) {
                    avg_time += result.parse_time;
                    avg_memory += result.memory_usage;
                    avg_nodes += result.ast_node_count;
                    success_count++;
                }
                
                std::cout << "  " << filenames[f] << ": "
                          << (result.success ? "成功" : "失败") << ", "
                          << result.parse_time << " ms, "
                          << result.memory_usage << " KB, "
                          << result.ast_node_count << " 节点" << std::endl;
            }
        }
        
        if (success_count > 0) {
            avg_time /= success_count;
            avg_memory /= success_count;
            avg_nodes /= success_count;
            
            std::cout << "  平均: "
                      << avg_time << " ms, "
                      << avg_memory << " KB, "
                      << avg_nodes << " 节点, "
                      << "成功率: " << (success_count * 100 / filenames.size()) << "%" << std::endl;
        } else {
            std::cout << "  没有成功解析任何文件" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    // 输出到CSV文件
    std::ofstream csv("parser_benchmark_results.csv");
    
    // 写入CSV表头
    csv << "解析器,语言,版本";
    for (const auto& filename : filenames) {
        std::string abs_filename = std::filesystem::absolute(filename).string();
        csv << ",时间(" << abs_filename << "),内存(" << abs_filename << "),"
            << "节点数(" << abs_filename << "),成功(" << abs_filename << ")";
    }
    csv << ",平均时间(ms),平均内存(KB),平均节点数,成功率(%)" << std::endl;
    
    // 写入每个解析器的结果
    for (size_t p = 0; p < parsers.size(); p++) {
        double avg_time = 0;
        size_t avg_memory = 0;
        size_t avg_nodes = 0;
        size_t success_count = 0;
        
        csv << parsers[p]->getName() << ","
            << parsers[p]->getLanguage() << ","
            << parsers[p]->getVersion();
        
        for (size_t f = 0; f < filenames.size(); f++) {
            if (f < all_results.size() && p < all_results[f].size()) {
                const auto& result = all_results[f][p];
                
                csv << "," << result.parse_time
                    << "," << result.memory_usage
                    << "," << result.ast_node_count
                    << "," << (result.success ? "true" : "false");
                
                if (result.success) {
                    avg_time += result.parse_time;
                    avg_memory += result.memory_usage;
                    avg_nodes += result.ast_node_count;
                    success_count++;
                }
            } else {
                csv << ",0,0,0,false";
            }
        }
        
        if (success_count > 0) {
            avg_time /= success_count;
            avg_memory /= success_count;
            avg_nodes /= success_count;
        }
        
        csv << "," << avg_time
            << "," << avg_memory
            << "," << avg_nodes
            << "," << (success_count * 100 / filenames.size()) << std::endl;
    }
    
    std::cout << "性能对比报告已保存到 parser_benchmark_results.csv" << std::endl;
}

void ParserManager::listParsers() const {
    std::cout << "可用的SMT解析器 (" << parsers.size() << "):" << std::endl;
    
    for (const auto& parser : parsers) {
        std::cout << "- " << parser->getName() << " (" 
                  << parser->getLanguage() << ", 版本: " 
                  << parser->getVersion() << ")" << std::endl;
        
        std::cout << "  特性: ";
        const auto& features = parser->getFeatures();
        for (size_t i = 0; i < features.size(); ++i) {
            std::cout << features[i];
            if (i < features.size() - 1) {
                std::cout << ", ";
            }
        }
        std::cout << std::endl;
    }
}

std::vector<std::string> ParserManager::getParserNames() const {
    std::vector<std::string> names;
    for (const auto& parser : parsers) {
        names.push_back(parser->getName());
    }
    return names;
}

std::shared_ptr<ParserInterface> ParserManager::getParserByName(const std::string& name) const {
    for (const auto& parser : parsers) {
        if (parser->getName() == name) {
            return parser;
        }
    }
    return nullptr;
}

ParseResult ParserManager::testFileWithParser(const std::string& filename, const std::string& parserName) {
    auto parser = getParserByName(parserName);
    if (!parser) {
        ParseResult result;
        result.success = false;
        result.errors.push_back("找不到解析器: " + parserName);
        return result;
    }
    
    std::string abs_filename = std::filesystem::absolute(filename).string();
    std::cout << "使用 " << parser->getName() << " 解析器测试文件: " << abs_filename << " (超时: " << g_timeout_seconds << "秒)" << std::endl;
    
    ParseResult result;
    try {
        result = parser->parse(filename);
    } catch (const std::exception& e) {
        result.success = false;
        result.result_code = ResultCode::CRASH;
        result.errors.push_back(std::string("解析器异常: ") + e.what());
    } catch (...) {
        result.success = false;
        result.result_code = ResultCode::CRASH;
        result.errors.push_back("未知异常");
    }
    
    // 输出结果
    std::cout << "  结果: " << (result.success ? "成功" : "失败") << std::endl;
    std::cout << "  解析时间: " << result.parse_time << " ms" << std::endl;
    std::cout << "  内存使用: " << result.memory_usage << " KB" << std::endl;
    std::cout << "  AST节点数量: " << result.ast_node_count << std::endl;
    
    if (!result.success && !result.errors.empty()) {
        std::cout << "  错误信息:" << std::endl;
        for (const auto& err : result.errors) {
            std::cout << "    " << err << std::endl;
        }
    }
    
    return result;
}

void ParserManager::benchmarkFilesWithParser(const std::vector<std::string>& filenames, const std::string& parserName) {
    auto parser = getParserByName(parserName);
    if (!parser) {
        std::cerr << "找不到解析器: " << parserName << std::endl;
        return;
    }
    
    std::vector<ParseResult> results;
    size_t success_count = 0;
    size_t failure_count = 0;
    size_t crash_count = 0;
    
    // 对每个文件执行测试
    for (const auto& filename : filenames) {
        ParseResult result;
        bool hadException = false;
        
        try {
            result = parser->parse(filename);
            if (result.success) {
                success_count++;
            } else {
                failure_count++;
            }
        } catch (const std::exception& e) {
            hadException = true;
            result.success = false;
            result.errors.push_back(std::string("解析过程异常: ") + e.what());
            crash_count++;
        } catch (...) {
            hadException = true;
            result.success = false;
            result.errors.push_back("解析过程发生未知异常或崩溃");
            crash_count++;
        }
        
        // 输出简要结果
        std::string abs_filename = std::filesystem::absolute(filename).string();
        std::cout << "文件: " << abs_filename;
        if (hadException) {
            std::cout << " - 异常/崩溃" << std::endl;
            if (!result.errors.empty()) {
                std::cout << "  错误: " << result.errors[0] << std::endl;
            }
        } else {
            std::cout << " - " << (result.success ? "成功" : "失败") << std::endl;
            if (!result.success && !result.errors.empty()) {
                std::cout << "  错误: " << result.errors[0] << std::endl;
            }
        }
        
        results.push_back(result);
    }
    
    // 生成报告
    generateSingleParserReport(parserName, filenames, results);
    
    // 输出摘要信息
    double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count) / filenames.size() * 100.0);
    double failure_rate = filenames.empty() ? 0 : (static_cast<double>(failure_count) / filenames.size() * 100.0);
    double crash_rate = filenames.empty() ? 0 : (static_cast<double>(crash_count) / filenames.size() * 100.0);
    
    std::cout << "\n===== " << parserName << " 解析器测试摘要 =====" << std::endl;
    std::cout << "总文件数: " << filenames.size() << std::endl;
    std::cout << "成功: " << success_count << " (" << std::fixed << std::setprecision(2) 
              << success_rate << "%)" << std::endl;
    std::cout << "失败: " << failure_count << " (" << std::fixed << std::setprecision(2) 
              << failure_rate << "%)" << std::endl;
    std::cout << "崩溃/异常: " << crash_count << " (" << std::fixed << std::setprecision(2) 
              << crash_rate << "%)" << std::endl;
}

void ParserManager::generateSingleParserReport(
    const std::string& parserName,
    const std::vector<std::string>& filenames,
    const std::vector<ParseResult>& results
) {
    // 创建CSV文件
    std::string filename = parserName + "_report.csv";
    std::ofstream report(filename);
    if (!report) {
        std::cerr << "无法创建报告文件: " << filename << std::endl;
        return;
    }
    
    // 写入CSV头
    report << "文件名,解析时间(ms),内存使用(KB),AST节点数量,结果" << std::endl;
    
    // 计算统计信息
    size_t success_count = 0;
    double total_time = 0;
    size_t total_memory = 0;
    size_t total_nodes = 0;
    
    // 写入每个文件的结果
    for (size_t i = 0; i < filenames.size() && i < results.size(); ++i) {
        std::string abs_filename = std::filesystem::absolute(filenames[i]).string();
        const auto& result = results[i];
        
        report << abs_filename << ",";
        report << result.parse_time << ",";
        report << result.memory_usage << ",";
        report << result.ast_node_count << ",";
        report << (result.success ? "成功" : "失败") << std::endl;
        
        // 更新统计信息
        if (result.success) {
            success_count++;
            total_time += result.parse_time;
            total_memory += result.memory_usage;
            total_nodes += result.ast_node_count;
        }
    }
    
    // 写入汇总统计
    double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count) / filenames.size() * 100.0);
    double avg_time = success_count > 0 ? (total_time / success_count) : 0;
    double avg_memory = success_count > 0 ? (static_cast<double>(total_memory) / success_count) : 0;
    double avg_nodes = success_count > 0 ? (static_cast<double>(total_nodes) / success_count) : 0;
    
    report << "平均值,";
    report << avg_time << ",";
    report << avg_memory << ",";
    report << avg_nodes << ",";
    report << success_rate << "%" << std::endl;
    
    std::cout << "生成报告: " << filename << std::endl;
}

// 重载版本：带输出文件名的benchmarkFiles
void ParserManager::benchmarkFiles(const std::vector<std::string>& filenames, const std::string& outputFilename) {
    // 准备结果矩阵
    std::vector<std::vector<ParseResult>> all_results;
    
    for (const auto& filename : filenames) {
        std::vector<ParseResult> file_results = testFile(filename);
        all_results.push_back(file_results);
    }
    
    // 生成对比报告
    generateReport(filenames, all_results, outputFilename);
}

// 重载版本：带输出文件名的generateReport
void ParserManager::generateReport(
    const std::vector<std::string>& filenames,
    const std::vector<std::vector<ParseResult>>& all_results,
    const std::string& outputFilename
) {
    // 输出到控制台
    std::cout << "\n========== SMT解析器性能对比报告 ==========\n" << std::endl;
    
    // 计算平均值
    for (size_t p = 0; p < parsers.size(); p++) {
        double avg_time = 0;
        size_t avg_memory = 0;
        size_t avg_nodes = 0;
        size_t success_count = 0;
        
        std::cout << parsers[p]->getName() << " (" << parsers[p]->getLanguage() << "):" << std::endl;
        
        for (size_t f = 0; f < filenames.size(); f++) {
            if (f < all_results.size() && p < all_results[f].size()) {
                const auto& result = all_results[f][p];
                
                if (result.success) {
                    avg_time += result.parse_time;
                    avg_memory += result.memory_usage;
                    avg_nodes += result.ast_node_count;
                    success_count++;
                }
                
                std::cout << "  " << filenames[f] << ": "
                          << (result.success ? "成功" : "失败") << ", "
                          << result.parse_time << " ms, "
                          << result.memory_usage << " KB, "
                          << result.ast_node_count << " 节点" << std::endl;
            }
        }
        
        if (success_count > 0) {
            avg_time /= success_count;
            avg_memory /= success_count;
            avg_nodes /= success_count;
            
            std::cout << "  平均: "
                      << avg_time << " ms, "
                      << avg_memory << " KB, "
                      << avg_nodes << " 节点, "
                      << "成功率: " << (success_count * 100 / filenames.size()) << "%" << std::endl;
        } else {
            std::cout << "  没有成功解析任何文件" << std::endl;
        }
        
        std::cout << std::endl;
    }
    
    // 输出到CSV文件（使用指定的文件名）
    std::ofstream csv(outputFilename);
    
    // 写入CSV表头
    csv << "解析器,语言,版本";
    for (const auto& filename : filenames) {
        std::string abs_filename = std::filesystem::absolute(filename).string();
        csv << ",时间(" << abs_filename << "),内存(" << abs_filename << "),"
            << "节点数(" << abs_filename << "),成功(" << abs_filename << ")";
    }
    csv << ",平均时间(ms),平均内存(KB),平均节点数,成功率(%)" << std::endl;
    
    // 写入每个解析器的结果
    for (size_t p = 0; p < parsers.size(); p++) {
        double avg_time = 0;
        size_t avg_memory = 0;
        size_t avg_nodes = 0;
        size_t success_count = 0;
        
        csv << parsers[p]->getName() << ","
            << parsers[p]->getLanguage() << ","
            << parsers[p]->getVersion();
        
        for (size_t f = 0; f < filenames.size(); f++) {
            if (f < all_results.size() && p < all_results[f].size()) {
                const auto& result = all_results[f][p];
                
                csv << "," << result.parse_time
                    << "," << result.memory_usage
                    << "," << result.ast_node_count
                    << "," << (result.success ? "true" : "false");
                
                if (result.success) {
                    avg_time += result.parse_time;
                    avg_memory += result.memory_usage;
                    avg_nodes += result.ast_node_count;
                    success_count++;
                }
            } else {
                csv << ",0,0,0,false";
            }
        }
        
        if (success_count > 0) {
            avg_time /= success_count;
            avg_memory /= success_count;
            avg_nodes /= success_count;
        }
        
        csv << "," << avg_time
            << "," << avg_memory
            << "," << avg_nodes
            << "," << (success_count * 100 / filenames.size()) << std::endl;
    }
    
    std::cout << "性能对比报告已保存到 " << outputFilename << std::endl;
}

// 重载版本：带输出文件名的benchmarkFilesWithParser
void ParserManager::benchmarkFilesWithParser(const std::vector<std::string>& filenames, const std::string& parserName, const std::string& outputFilename) {
    auto parser = getParserByName(parserName);
    if (!parser) {
        std::cerr << "找不到解析器: " << parserName << std::endl;
        return;
    }
    
    std::vector<ParseResult> results;
    size_t success_count = 0;
    size_t failure_count = 0;
    size_t crash_count = 0;
    
    // 对每个文件执行测试
    for (const auto& filename : filenames) {
        ParseResult result;
        bool hadException = false;
        
        try {
            result = parser->parse(filename);
            if (result.success) {
                success_count++;
            } else {
                failure_count++;
            }
        } catch (const std::exception& e) {
            hadException = true;
            result.success = false;
            result.errors.push_back(std::string("解析过程异常: ") + e.what());
            crash_count++;
        } catch (...) {
            hadException = true;
            result.success = false;
            result.errors.push_back("解析过程发生未知异常或崩溃");
            crash_count++;
        }
        
        // 输出简要结果
        std::string abs_filename = std::filesystem::absolute(filename).string();
        std::cout << "文件: " << abs_filename;
        if (hadException) {
            std::cout << " - 异常/崩溃" << std::endl;
            if (!result.errors.empty()) {
                std::cout << "  错误: " << result.errors[0] << std::endl;
            }
        } else {
            std::cout << " - " << (result.success ? "成功" : "失败") << std::endl;
            if (!result.success && !result.errors.empty()) {
                std::cout << "  错误: " << result.errors[0] << std::endl;
            }
        }
        
        results.push_back(result);
    }
    
    // 生成报告
    generateSingleParserReport(parserName, filenames, results, outputFilename);
    
    // 输出摘要信息
    double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count) / filenames.size() * 100.0);
    double failure_rate = filenames.empty() ? 0 : (static_cast<double>(failure_count) / filenames.size() * 100.0);
    double crash_rate = filenames.empty() ? 0 : (static_cast<double>(crash_count) / filenames.size() * 100.0);
    
    std::cout << "\n===== " << parserName << " 解析器测试摘要 =====" << std::endl;
    std::cout << "总文件数: " << filenames.size() << std::endl;
    std::cout << "成功: " << success_count << " (" << std::fixed << std::setprecision(2) 
              << success_rate << "%)" << std::endl;
    std::cout << "失败: " << failure_count << " (" << std::fixed << std::setprecision(2) 
              << failure_rate << "%)" << std::endl;
    std::cout << "崩溃/异常: " << crash_count << " (" << std::fixed << std::setprecision(2) 
              << crash_rate << "%)" << std::endl;
}

// 重载版本：带输出文件名的generateSingleParserReport
void ParserManager::generateSingleParserReport(
    const std::string& parserName,
    const std::vector<std::string>& filenames,
    const std::vector<ParseResult>& results,
    const std::string& outputFilename
) {
    // 创建CSV文件
    std::ofstream report(outputFilename);
    if (!report) {
        std::cerr << "无法创建报告文件: " << outputFilename << std::endl;
        return;
    }
    
    // 写入CSV头
    report << "文件名,解析时间(ms),内存使用(KB),AST节点数量,结果" << std::endl;
    
    // 计算统计信息
    size_t success_count = 0;
    double total_time = 0;
    size_t total_memory = 0;
    size_t total_nodes = 0;
    
    // 写入每个文件的结果
    for (size_t i = 0; i < filenames.size() && i < results.size(); ++i) {
        std::string abs_filename = std::filesystem::absolute(filenames[i]).string();
        const auto& result = results[i];
        
        report << abs_filename << ",";
        report << result.parse_time << ",";
        report << result.memory_usage << ",";
        report << result.ast_node_count << ",";
        report << (result.success ? "成功" : "失败") << std::endl;
        
        // 更新统计信息
        if (result.success) {
            success_count++;
            total_time += result.parse_time;
            total_memory += result.memory_usage;
            total_nodes += result.ast_node_count;
        }
    }
    
    // 写入汇总统计
    double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count) / filenames.size() * 100.0);
    double avg_time = success_count > 0 ? (total_time / success_count) : 0;
    double avg_memory = success_count > 0 ? (static_cast<double>(total_memory) / success_count) : 0;
    double avg_nodes = success_count > 0 ? (static_cast<double>(total_nodes) / success_count) : 0;
    
    report << "平均值,";
    report << avg_time << ",";
    report << avg_memory << ",";
    report << avg_nodes << ",";
    report << success_rate << "%" << std::endl;
    
    std::cout << "生成报告: " << outputFilename << std::endl;
}

// ======== Z3Parser 实现 ========
ParseResult Z3Parser::parse(const std::string& filename) {
    ParseResult result;
    std::string exe = resolveExternalPath(parser_path);
    namespace fs = std::filesystem;
    if (fs::exists(exe) && fs::is_directory(fs::path(exe)))
        exe = (fs::path(exe) / "z3_parser").string();
    std::string cmd = exe + " \"" + std::filesystem::absolute(filename).string() + "\"";
    
    ProcessRunResult pr = runExternalCommand(cmd);
    std::string output = pr.stdout_output;
    result.parse_time = pr.wall_time_ms;
    result.peak_rss_kb = pr.peak_rss_kb;
    result.exit_code = pr.exit_code;
    result.stderr_snippet = pr.stderr_output;
    if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
    if (pr.timed_out) {
        result.success = false;
        result.result_code = ResultCode::TIMEOUT;
        result.errors.push_back("命令执行超时");
        return result;
    }
    if (pr.exit_code != 0) {
        result.success = false;
        result.result_code = resultCodeFromStderr(pr.stderr_output);
    }
    
    try {
        SimpleJson::Value json = SimpleJson::Parser::parse(output);
        
        // 填充结果结构
        result.success = json["success"].getBool();
        result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
        result.parse_time = json["parse_time"].getNumber();
        result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
        result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
        
        // 获取错误信息
        if (json["errors"].isArray()) {
            const auto& errors = json["errors"].getArray();
            for (const auto& err : errors) {
                result.errors.push_back(err.getString());
            }
        }
        
        // parsing_method 为元数据，不放入 errors
    } catch (const std::exception& e) {
        result.success = false;
        result.result_code = ResultCode::PARSE_ERROR;
        result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
        result.errors.push_back("原始输出: " + output);
    }
    
    return result;
}

// ======== ANTLR4Parser 实现 ========
ParseResult ANTLR4Parser::parse(const std::string& filename) {
    ParseResult result;
    
    std::string abs_antlr4_path = resolveExternalPath(parser_path);
    std::string abs_filename_path = std::filesystem::absolute(filename).string();
    
    std::string antlr_jar = abs_antlr4_path + "/antlr-4.13.2-complete.jar";
    std::string classpath = "\"" + abs_antlr4_path + ":" + antlr_jar + "\"";
    std::string cmd = "java -cp " + classpath + " antlr4_parser \"" + abs_filename_path + "\"";
    
    ProcessRunResult pr = runExternalCommand(cmd);
    std::string output = pr.stdout_output;
    result.parse_time = pr.wall_time_ms;
    result.peak_rss_kb = pr.peak_rss_kb;
    result.exit_code = pr.exit_code;
    result.stderr_snippet = pr.stderr_output;
    if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
    if (pr.timed_out) {
        result.success = false;
        result.result_code = ResultCode::TIMEOUT;
        result.errors.push_back("命令执行超时");
        return result;
    }
    if (pr.exit_code != 0) {
        result.success = false;
        result.result_code = resultCodeFromStderr(pr.stderr_output);
    }
    
    try {
        SimpleJson::Value json = SimpleJson::Parser::parse(output);
        
        result.success = json["success"].getBool();
        result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
        result.parse_time = json["parse_time"].getNumber();
        result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
        result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
        
        // 获取错误信息
        if (json["errors"].isArray()) {
            const auto& errors = json["errors"].getArray();
            for (const auto& err : errors) {
                result.errors.push_back(err.getString());
            }
        }
        
        // parsing_method 为元数据，不放入 errors
    } catch (const std::exception& e) {
        result.success = false;
        result.result_code = ResultCode::PARSE_ERROR;
        result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
        result.errors.push_back("原始输出: " + output);
    }
    
    return result;
}

// ======== Cvc5Parser 实现 ========
Cvc5Parser::Cvc5Parser(const std::string& path)
    : ExternalParser(
          path,
          "cvc5",
          "1.0",
          "C++",
          {"SMT-LIB 2.6", "cvc5 求解器前端", "https://github.com/cvc5/cvc5"}
      ),
      cvc5_bin_(""),
      cvc5_parser_exe_("") {
    namespace fs = std::filesystem;
    std::string resolved = resolveExternalPath(path);
    fs::path base(resolved);
    if (fs::exists(base) && fs::is_directory(base)) {
        // 优先：本目录编译的 cvc5_parser（C API，输出 JSON）
        for (const auto& cand : { base / "build" / "cvc5_parser", base / "cvc5_parser" }) {
            if (fs::exists(cand) && fs::is_regular_file(cand)) {
                cvc5_parser_exe_ = cand.string();
                break;
            }
        }
        for (const auto& sub : { base / "build" / "bin" / "cvc5", base / "bin" / "cvc5" }) {
            if (fs::exists(sub) && fs::is_regular_file(sub)) {
                cvc5_bin_ = sub.string();
                break;
            }
        }
        if (cvc5_bin_.empty()) {
            for (const auto& entry : fs::directory_iterator(base)) {
                if (!entry.is_directory()) continue;
                std::string name = entry.path().filename().string();
                bool is_prebuilt = (name.find("cvc5-Linux") == 0 || name.find("cvc5-") == 0);
                if (is_prebuilt) {
                    fs::path cand = entry.path() / "bin" / "cvc5";
                    if (fs::exists(cand) && fs::is_regular_file(cand)) {
                        cvc5_bin_ = cand.string();
                        break;
                    }
                }
            }
        }
    }
    if (cvc5_bin_.empty()) {
        if (fs::exists(base) && fs::is_regular_file(base))
            cvc5_bin_ = resolved;
        else
            cvc5_bin_ = "cvc5";
    }
}

ParseResult Cvc5Parser::parse(const std::string& filename) {
    ParseResult result;
    std::string abs_path = std::filesystem::absolute(filename).string();
    if (!cvc5_parser_exe_.empty() && access(cvc5_parser_exe_.c_str(), F_OK) == 0) {
        std::string cmd = cvc5_parser_exe_ + " \"" + abs_path + "\"";
        ProcessRunResult pr = runExternalCommand(cmd);
        std::string output = pr.stdout_output;
        result.parse_time = pr.wall_time_ms;
        result.peak_rss_kb = pr.peak_rss_kb;
        result.exit_code = pr.exit_code;
        result.stderr_snippet = pr.stderr_output;
        if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
        if (pr.timed_out) {
            result.success = false;
            result.result_code = ResultCode::TIMEOUT;
            result.errors.push_back("命令执行超时");
            return result;
        }
        try {
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            result.success = json["success"].getBool();
            result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
            result.parse_time = json["parse_time"].getNumber();
            result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
            result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
            if (json["errors"].isArray())
                for (const auto& e : json["errors"].getArray())
                    result.errors.push_back(e.getString());
        } catch (...) {
            result.success = false;
            if (result.result_code == ResultCode::UNKNOWN) result.result_code = ResultCode::PARSE_ERROR;
            result.errors.push_back("解析 cvc5_parser 输出失败");
            if (!output.empty()) result.errors.push_back("原始输出: " + output.substr(0, 200));
        }
        return result;
    }
    if (cvc5_bin_.empty()) {
        result.success = false;
        result.result_code = ResultCode::UNKNOWN;
        result.errors.push_back("cvc5 可执行文件未找到");
        return result;
    }
    std::string cmd = cvc5_bin_ + " \"" + abs_path + "\"";
    ProcessRunResult pr = runExternalCommand(cmd);
    result.parse_time = pr.wall_time_ms;
    result.peak_rss_kb = pr.peak_rss_kb;
    result.exit_code = pr.exit_code;
    result.stderr_snippet = pr.stderr_output;
    if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
    if (pr.timed_out) {
        result.success = false;
        result.result_code = ResultCode::TIMEOUT;
        result.errors.push_back("命令执行超时");
        return result;
    }
    result.success = (pr.exit_code == 0);
    result.result_code = result.success ? ResultCode::OK : resultCodeFromStderr(pr.stderr_output);
    if (!pr.stderr_output.empty() && !result.success) {
        std::istringstream iss(pr.stderr_output);
        std::string line;
        while (std::getline(iss, line))
            if (!line.empty()) result.errors.push_back(line);
    }
    return result;
}

// ======== SmtSwitchParser 实现 ========
SmtSwitchParser::SmtSwitchParser(const std::string& path)
    : ExternalParser(
          path,
          "smt-switch",
          "1.0",
          "C++",
          {"SMT-LIB 2.6", "通用 SMT API", "https://github.com/stanford-centaur/smt-switch"}
      ),
      parser_exe_("") {
    namespace fs = std::filesystem;
    std::string resolved = resolveExternalPath(path);
    fs::path base(resolved);
    if (fs::exists(base) && fs::is_directory(base)) {
        // 固定路径：本目录 build/smt_switch_parser（调用自己文件夹内的可执行文件）
        fs::path cand = base / "build" / "smt_switch_parser";
        if (fs::exists(cand) && fs::is_regular_file(cand)) {
            parser_exe_ = cand.string();
        }
        if (parser_exe_.empty()) {
            // 从 add_subdirectory(smt-switch-1.0.6) 构建时在 build/smt-switch-1.0.6/smt_switch_parser
            cand = base / "build" / "smt-switch-1.0.6" / "smt_switch_parser";
            if (fs::exists(cand) && fs::is_regular_file(cand)) {
                parser_exe_ = cand.string();
            }
        }
        if (parser_exe_.empty()) {
            // 发布目录：smt-switch-1.0.6/build/smt_switch_parser
            for (const auto& entry : fs::directory_iterator(base)) {
                if (!entry.is_directory()) continue;
                std::string name = entry.path().filename().string();
                if (name.find("smt-switch-") == 0) {
                    cand = entry.path() / "build" / "smt_switch_parser";
                    if (fs::exists(cand) && fs::is_regular_file(cand)) {
                        parser_exe_ = cand.string();
                        break;
                    }
                }
            }
        }
    }
    if (parser_exe_.empty() && fs::exists(base) && fs::is_regular_file(base))
        parser_exe_ = resolved;
}

ParseResult SmtSwitchParser::parse(const std::string& filename) {
    ParseResult result;
    std::string exe = parser_exe_.empty() ? parser_path : parser_exe_;
    if (exe.empty() || access(exe.c_str(), F_OK) != 0) {
        result.success = false;
        result.result_code = ResultCode::UNKNOWN;
        result.errors.push_back("smt_switch_parser 可执行文件未找到，请参考 external/smt-switch/README.md 编译");
        return result;
    }
    std::string abs_path = std::filesystem::absolute(filename).string();
    std::string cmd = exe + " \"" + abs_path + "\"";
    ProcessRunResult pr = runExternalCommand(cmd);
    std::string output = pr.stdout_output;
    result.parse_time = pr.wall_time_ms;
    result.peak_rss_kb = pr.peak_rss_kb;
    result.exit_code = pr.exit_code;
    result.stderr_snippet = pr.stderr_output;
    if (pr.peak_rss_kb > 0) result.memory_usage = pr.peak_rss_kb;
    if (pr.timed_out) {
        result.success = false;
        result.result_code = ResultCode::TIMEOUT;
        result.errors.push_back("命令执行超时");
        return result;
    }
    if (pr.exit_code != 0)
        result.result_code = resultCodeFromStderr(pr.stderr_output);
    try {
        SimpleJson::Value json = SimpleJson::Parser::parse(output);
        result.success = json["success"].getBool();
        result.result_code = result.success ? ResultCode::OK : ResultCode::PARSE_ERROR;
        result.parse_time = json["parse_time"].getNumber();
        result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
        result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
        if (json["errors"].isArray())
            for (const auto& e : json["errors"].getArray())
                result.errors.push_back(e.getString());
    } catch (...) {
        result.success = false;
        if (result.result_code == ResultCode::UNKNOWN) result.result_code = ResultCode::PARSE_ERROR;
        result.errors.push_back("解析 smt-switch 输出失败");
        if (!output.empty()) result.errors.push_back("原始输出: " + output.substr(0, 200));
    }
    return result;
}

} // namespace SMTComparison 