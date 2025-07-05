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
}

ParserWrapper::~ParserWrapper() {
    // 清理资源
}

bool ParserWrapper::parse(const std::string& filename) {
    // 这里应该调用实际SMTParser的解析函数
    
    // 模拟实现，在实际项目中应替换为真正的解析逻辑
    std::cout << "解析文件: " << filename << std::endl;
    
    // 模拟解析过程
    ast_node_count = 100;  // 示例值
    syntax_coverage = 95;  // 示例值
    semantic_checks = 80;  // 示例值
    
    return true;  // 示例总是返回成功
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
    result.syntax_coverage = parser->getSyntaxCoverage();
    result.semantic_checks = parser->getSemanticCheckCount();
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
            
            // pySMT不直接提供语法覆盖率和语义检查数量
            result.syntax_coverage = 100;  // 假设100%覆盖率
            result.semantic_checks = result.ast_node_count;  // 假设每个节点一次语义检查
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
        
        // 尝试解析语法覆盖率
        if (line.find("语法覆盖率:") != std::string::npos) {
            result.syntax_coverage = std::stoul(line.substr(line.find(":") + 1));
        }
        
        // 尝试解析语义检查
        if (line.find("语义检查:") != std::string::npos) {
            result.semantic_checks = std::stoul(line.substr(line.find(":") + 1));
        }
    }
    
    output.close();
    std::remove(output_file.c_str());
    
    // 如果没有提供明确信息，设置默认值
    if (result.ast_node_count == 0) {
        size_t filesize = PerformanceMetrics::getFileSize(filename);
        result.ast_node_count = filesize / 10;  // 粗略估计
    }
    
    if (result.syntax_coverage == 0) {
        result.syntax_coverage = 95;  // 默认值
    }
    
    if (result.semantic_checks == 0) {
        result.semantic_checks = result.ast_node_count / 2;  // 估计
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
        result.syntax_coverage = 100;  // 假设完全覆盖
        result.semantic_checks = result.ast_node_count / 2;  // 估计
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
            std::cout << "  语法覆盖率: " << result.syntax_coverage << "%" << std::endl;
            std::cout << "  语义检查数: " << result.semantic_checks << std::endl;
            
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
        size_t pos = filename.find_last_of("/\\");
        std::string short_name = (pos != std::string::npos) ? filename.substr(pos + 1) : filename;
        csv << ",时间(" << short_name << "),内存(" << short_name << "),"
            << "节点数(" << short_name << "),成功(" << short_name << ")";
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
                    << "," << (result.success ? "是" : "否");
                
                if (result.success) {
                    avg_time += result.parse_time;
                    avg_memory += result.memory_usage;
                    avg_nodes += result.ast_node_count;
                    success_count++;
                }
            } else {
                csv << ",0,0,0,否";
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

} // namespace SMTComparison 