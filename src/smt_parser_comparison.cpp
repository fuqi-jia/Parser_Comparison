#include "smt_parser_comparison.h"
#include "simple_json.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <random>
#include <filesystem>

namespace SMTComparison {

// 执行外部命令并获取输出的帮助函数
std::string exec(const std::string& cmd) {
    std::array<char, 4096> buffer;
    std::string result;
    std::unique_ptr<FILE, int(*)(FILE*)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) {
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
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
        
        // 记录开始时的内存使用
        size_t initial_memory = PerformanceMetrics::getCurrentMemoryUsage();
        
        // 调用外部程序解析文件
        std::string output;
        double parse_time = PerformanceMetrics::measureExecutionTime([&]() {
            output = exec(cmd);
        });
        
        // 计算内存使用
        size_t final_memory = PerformanceMetrics::getCurrentMemoryUsage();
        result.memory_usage = final_memory - initial_memory;
        result.parse_time = parse_time;
        
        // 解析JSON输出
        try {
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            
            // 填充结果结构
            result.success = json["success"].getBool();
            // 只使用wrapper报告的解析时间，忽略进程启动时间
            result.parse_time = json["parse_time"].getNumber();
            // 使用wrapper报告的内存使用，更准确
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
        }
    } catch (const std::exception& e) {
        result.success = false;
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
        
        // 执行Python脚本
        std::string output = exec(cmd);
        
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
        result.errors.push_back(std::string("执行pySMT解析器失败: ") + e.what());
    }
    
    return result;
}

// ======== ANTLRParser 实现 ========
ParseResult ANTLRParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 创建临时输出文件
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1000, 9999);
    std::string output_file = "/tmp/antlr_result_" + std::to_string(dis(gen)) + ".txt";
    
    // 执行ANTLR解析器
    std::string cmd = parser_path + " " + filename + " > " + output_file + " 2>&1";
    
    // 记录开始时间和内存
    size_t memory_before = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 测量执行时间
    result.parse_time = PerformanceMetrics::measureExecutionTime([&]() {
        int ret = system(cmd.c_str()); // 处理返回值，避免警告
        if (ret != 0) {
            std::cerr << "ANTLR命令执行失败，返回值: " << ret << std::endl;
        }
    });
    
    // 计算内存使用
    size_t memory_after = PerformanceMetrics::getCurrentMemoryUsage();
    result.memory_usage = memory_after - memory_before;
    
    // 读取结果
    std::ifstream output(output_file);
    std::string line;
    bool has_errors = false;
    
    while (std::getline(output, line)) {
        if (line.find("ERROR") != std::string::npos || 
            line.find("Exception") != std::string::npos) {
            has_errors = true;
            result.errors.push_back(line);
        }
        
        // 尝试解析节点计数
        if (line.find("AST节点数:") != std::string::npos) {
            result.ast_node_count = std::stoul(line.substr(line.find(":") + 1));
        }
    }
    
    output.close();
    std::remove(output_file.c_str());
    
    // 如果没有提供明确信息，设置默认值
    if (result.ast_node_count == 0) {
        size_t filesize = PerformanceMetrics::getFileSize(filename);
        result.ast_node_count = filesize / 10;  // 粗略估计
    }
    
    result.success = !has_errors;
    return result;
}

// ======== JSMTLIBParser 实现 ========
ParseResult JSMTLIBParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 创建临时输出文件
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1000, 9999);
    std::string output_file = "/tmp/jsmtlib_result_" + std::to_string(dis(gen)) + ".txt";
    
    // 执行jSMTLIB解析器
    std::string cmd = "java -jar " + parser_path + " -parse " + filename + " > " + output_file + " 2>&1";
    
    // 记录开始时间和内存
    size_t memory_before = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 测量执行时间
    result.parse_time = PerformanceMetrics::measureExecutionTime([&]() {
        int ret = system(cmd.c_str()); // 处理返回值，避免警告
        if (ret != 0) {
            std::cerr << "jSMTLIB命令执行失败，返回值: " << ret << std::endl;
        }
    });
    
    // 计算内存使用
    size_t memory_after = PerformanceMetrics::getCurrentMemoryUsage();
    result.memory_usage = memory_after - memory_before;
    
    // 读取结果
    std::ifstream output(output_file);
    std::string line;
    bool has_errors = false;
    
    while (std::getline(output, line)) {
        if (line.find("ERROR") != std::string::npos || 
            line.find("Exception") != std::string::npos) {
            has_errors = true;
            result.errors.push_back(line);
        }
    }
    
    output.close();
    std::remove(output_file.c_str());
    
    result.success = !has_errors;
    
    // jSMTLIB没有直接提供这些信息，设置为默认值或估计值
    if (result.success) {
        // 估计AST节点数基于文件大小
        size_t filesize = PerformanceMetrics::getFileSize(filename);
        result.ast_node_count = filesize / 10;  // 粗略估计
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
        
        // 尝试添加ANTLR解析器
        try {
            addParser(std::make_shared<ANTLRParser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化ANTLR解析器: " << e.what() << std::endl;
        }
        
        // 尝试添加jSMTLIB解析器
        try {
            addParser(std::make_shared<JSMTLIBParser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化jSMTLIB解析器: " << e.what() << std::endl;
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
            std::cout << "使用 " << parser->getName() << " 解析 " << abs_filename << std::endl;
            
            ParseResult result = parser->parse(filename);
            
            std::cout << "  解析状态: " << (result.success ? "成功" : "失败") << std::endl;
            std::cout << "  解析时间: " << result.parse_time << " ms" << std::endl;
            std::cout << "  内存使用: " << result.memory_usage << " KB" << std::endl;
            std::cout << "  AST节点数: " << result.ast_node_count << std::endl;
            
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
    std::cout << "使用 " << parser->getName() << " 解析器测试文件: " << abs_filename << std::endl;
    
    ParseResult result;
    try {
        result = parser->parse(filename);
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("解析器异常: ") + e.what());
    } catch (...) {
        result.success = false;
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

} // namespace SMTComparison 