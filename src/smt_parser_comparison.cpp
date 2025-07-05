#include "smt_parser_comparison.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <random>

// 如果可以，引入实际SMTParser的头文件
// #include "SMTParser/parser.h" 

namespace SMTComparison {

// ======== ParserWrapper 实现 ========
ParserWrapper::ParserWrapper() {
    // 这里应该初始化对实际解析器的引用
    parser = std::make_shared<SMTParser::Parser>();
}

ParserWrapper::~ParserWrapper() {
    // 清理资源
}

bool ParserWrapper::parse(const std::string& filename) {
    // 这里应该调用实际SMTParser的解析函数
    return parser->parse(filename);
}

// ======== NativeParser 实现 ========
NativeParser::NativeParser() : parser(std::make_shared<ParserWrapper>()) {}

ParseResult NativeParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 记录开始时的内存使用
    size_t memory_before = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 测量解析时间
    result.parse_time = PerformanceMetrics::measureExecutionTime([&]() {
        result.success = parser->parse(filename);
    });
    
    // 计算内存使用
    size_t memory_after = PerformanceMetrics::getCurrentMemoryUsage();
    result.memory_usage = memory_after - memory_before;
    
    // 从解析器中获取更多信息
    result.ast_node_count = parser->getASTNodeCount();
    result.errors = parser->getErrors();
    
    return result;
}

// ======== PySMTParser 实现 ========
ParseResult PySMTParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 创建唯一的临时文件名
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1000, 9999);
    std::string temp_script = "/tmp/pysmt_parse_" + std::to_string(dis(gen)) + ".py";
    std::string output_file = "/tmp/pysmt_result_" + std::to_string(dis(gen)) + ".txt";
    
    // 写入Python脚本
    std::ofstream script(temp_script);
    script << "import time\n";
    script << "import resource\n";
    script << "import sys\n";
    script << "from pysmt.smtlib.parser import SmtLibParser\n\n";
    script << "try:\n";
    script << "    # 记录开始时间和内存\n";
    script << "    start_time = time.time()\n";
    script << "    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n\n";
    script << "    # 创建解析器并解析文件\n";
    script << "    parser = SmtLibParser()\n";
    script << "    script = parser.get_script_fname('" << filename << "')\n\n";
    script << "    # 记录结束时间和内存\n";
    script << "    end_time = time.time()\n";
    script << "    end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n\n";
    script << "    # 计算AST节点数\n";
    script << "    node_count = 0\n";
    script << "    for cmd in script.commands:\n";
    script << "        if hasattr(cmd.args[0], 'size'):\n";
    script << "            node_count += cmd.args[0].size()\n\n";
    script << "    # 写入结果\n";
    script << "    with open('" << output_file << "', 'w') as f:\n";
    script << "        f.write('SUCCESS\\n')\n";
    script << "        f.write(f'PARSE_TIME:{(end_time - start_time) * 1000:.2f}\\n')\n";
    script << "        f.write(f'MEMORY_USAGE:{end_mem - start_mem}\\n')\n";
    script << "        f.write(f'AST_NODES:{node_count}\\n')\n";
    script << "except Exception as e:\n";
    script << "    with open('" << output_file << "', 'w') as f:\n";
    script << "        f.write('FAILURE\\n')\n";
    script << "        f.write(f'ERROR:{str(e)}\\n')\n";
    script.close();
    
    // 执行Python脚本
    std::string cmd = python_path + " " + temp_script;
    try {
        exec(cmd);
        
        // 读取结果
        std::ifstream output(output_file);
        std::string line;
        
        // 读取第一行判断成功与否
        std::getline(output, line);
        result.success = (line == "SUCCESS");
        
        if (result.success) {
            // 读取解析时间
            std::getline(output, line);
            result.parse_time = std::stod(line.substr(line.find(":") + 1));
            
            // 读取内存使用
            std::getline(output, line);
            result.memory_usage = std::stoul(line.substr(line.find(":") + 1));
            
            // 读取AST节点数
            std::getline(output, line);
            result.ast_node_count = std::stoul(line.substr(line.find(":") + 1));
        } else {
            // 读取错误信息
            std::getline(output, line);
            result.errors.push_back(line.substr(line.find(":") + 1));
        }
        
        output.close();
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("执行错误: ") + e.what());
    }
    
    // 清理临时文件
    std::remove(temp_script.c_str());
    std::remove(output_file.c_str());
    
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
            std::cout << "使用 " << parser->getName() << " 解析 " << filename << std::endl;
            
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
        
        // 为每个解析器生成单独的CSV文件
        std::string safe_name = parsers[p]->getName();
        // 替换掉文件名中的特殊字符
        std::replace(safe_name.begin(), safe_name.end(), ' ', '_');
        std::replace(safe_name.begin(), safe_name.end(), ':', '-');
        std::replace(safe_name.begin(), safe_name.end(), '/', '_');
        std::replace(safe_name.begin(), safe_name.end(), '\\', '_');
        std::string csv_filename = safe_name + "_results.csv";
        
        std::ofstream csv(csv_filename);
        
        // 写入CSV表头
        csv << "文件名,解析成功,解析时间(ms),内存使用(KB),AST节点数" << std::endl;
        
        // 写入每个文件的结果
        for (size_t f = 0; f < filenames.size(); f++) {
            if (f < all_results.size() && p < all_results[f].size()) {
                const auto& result = all_results[f][p];
                
                // 提取文件名（不含路径）
                size_t pos = filenames[f].find_last_of("/\\");
                std::string short_name = (pos != std::string::npos) ? filenames[f].substr(pos + 1) : filenames[f];
                
                csv << short_name << ","
                    << (result.success ? "true" : "false") << ","
                    << result.parse_time << ","
                    << result.memory_usage << ","
                    << result.ast_node_count << std::endl;
            }
        }
        
        // 添加平均值和成功率
        csv << "平均值,"
            << (success_count > 0 ? "成功率:" + std::to_string(success_count * 100 / filenames.size()) + "%" : "无成功解析") << ","
            << (success_count > 0 ? avg_time : 0) << ","
            << (success_count > 0 ? avg_memory : 0) << ","
            << (success_count > 0 ? avg_nodes : 0) << std::endl;
        
        std::cout << "  结果已保存到 " << csv_filename << std::endl;
    }
    
    // 仍然生成一个总体比较的CSV文件
    std::ofstream summary_csv("parser_benchmark_summary.csv");
    
    // 写入摘要表头
    summary_csv << "解析器,语言,版本,平均解析时间(ms),平均内存使用(KB),平均AST节点数,成功率(%)" << std::endl;
    
    // 写入每个解析器的汇总结果
    for (size_t p = 0; p < parsers.size(); p++) {
        double avg_time = 0;
        size_t avg_memory = 0;
        size_t avg_nodes = 0;
        size_t success_count = 0;
        
        // 计算平均值
        for (size_t f = 0; f < filenames.size(); f++) {
            if (f < all_results.size() && p < all_results[f].size()) {
                const auto& result = all_results[f][p];
                if (result.success) {
                    avg_time += result.parse_time;
                    avg_memory += result.memory_usage;
                    avg_nodes += result.ast_node_count;
                    success_count++;
                }
            }
        }
        
        if (success_count > 0) {
            avg_time /= success_count;
            avg_memory /= success_count;
            avg_nodes /= success_count;
        }
        
        summary_csv << parsers[p]->getName() << ","
                    << parsers[p]->getLanguage() << ","
                    << parsers[p]->getVersion() << ","
                    << avg_time << ","
                    << avg_memory << ","
                    << avg_nodes << ","
                    << (success_count * 100 / filenames.size()) << std::endl;
    }
    
    std::cout << "解析器性能比较摘要已保存到 parser_benchmark_summary.csv" << std::endl;
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

// 新增方法：获取所有解析器名称
std::vector<std::string> ParserManager::getParserNames() const {
    std::vector<std::string> names;
    for (const auto& parser : parsers) {
        names.push_back(parser->getName());
    }
    return names;
}

// 新增方法：通过名称获取解析器
std::shared_ptr<ParserInterface> ParserManager::getParserByName(const std::string& name) const {
    for (const auto& parser : parsers) {
        if (parser->getName() == name) {
            return parser;
        }
    }
    return nullptr;
}

// 新增方法：测试特定解析器的性能
ParseResult ParserManager::testFileWithParser(const std::string& filename, const std::string& parserName) {
    auto parser = getParserByName(parserName);
    if (!parser) {
        throw std::runtime_error("找不到名为 '" + parserName + "' 的解析器");
    }
    
    try {
        std::cout << "使用 " << parser->getName() << " 解析 " << filename << std::endl;
        
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
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "  测试过程中出错: " << e.what() << std::endl;
        
        ParseResult errorResult;
        errorResult.success = false;
        errorResult.errors.push_back(e.what());
        return errorResult;
    }
}

// 新增方法：对特定解析器进行基准测试
void ParserManager::benchmarkFilesWithParser(const std::vector<std::string>& filenames, const std::string& parserName) {
    std::vector<ParseResult> results;
    
    for (const auto& filename : filenames) {
        results.push_back(testFileWithParser(filename, parserName));
    }
    
    // 生成单个解析器的报告
    generateSingleParserReport(parserName, filenames, results);
}

// 新增方法：生成单个解析器的报告
void ParserManager::generateSingleParserReport(
    const std::string& parserName,
    const std::vector<std::string>& filenames,
    const std::vector<ParseResult>& results
) {
    // 输出到控制台
    std::cout << "\n========== " << parserName << " 性能报告 ==========\n" << std::endl;
    
    // 计算平均值
    double avg_time = 0;
    size_t avg_memory = 0;
    size_t avg_nodes = 0;
    size_t success_count = 0;
    
    for (size_t f = 0; f < filenames.size() && f < results.size(); f++) {
        const auto& result = results[f];
        
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
    
    // 为解析器生成CSV文件
    std::string safe_name = parserName;
    // 替换掉文件名中的特殊字符
    std::replace(safe_name.begin(), safe_name.end(), ' ', '_');
    std::replace(safe_name.begin(), safe_name.end(), ':', '-');
    std::replace(safe_name.begin(), safe_name.end(), '/', '_');
    std::replace(safe_name.begin(), safe_name.end(), '\\', '_');
    std::string csv_filename = safe_name + "_results.csv";
    
    std::ofstream csv(csv_filename);
    
    // 写入CSV表头
    csv << "文件名,解析成功,解析时间(ms),内存使用(KB),AST节点数" << std::endl;
    
    // 写入每个文件的结果
    for (size_t f = 0; f < filenames.size() && f < results.size(); f++) {
        const auto& result = results[f];
        
        // 提取文件名（不含路径）
        size_t pos = filenames[f].find_last_of("/\\");
        std::string short_name = (pos != std::string::npos) ? filenames[f].substr(pos + 1) : filenames[f];
        
        csv << short_name << ","
            << (result.success ? "true" : "false") << ","
            << result.parse_time << ","
            << result.memory_usage << ","
            << result.ast_node_count << std::endl;
    }
    
    // 添加平均值和成功率
    csv << "平均值,"
        << (success_count > 0 ? "成功率:" + std::to_string(success_count * 100 / filenames.size()) + "%" : "无成功解析") << ","
        << (success_count > 0 ? avg_time : 0) << ","
        << (success_count > 0 ? avg_memory : 0) << ","
        << (success_count > 0 ? avg_nodes : 0) << std::endl;
    
    std::cout << "  结果已保存到 " << csv_filename << std::endl;
}

} // namespace SMTComparison 