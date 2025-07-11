#pragma once

#include "parser_interface.h"
#include "native_parser.h"
#include "pysmt_parser.h"
#include "external_parser.h"
#include <memory>
#include <vector>
#include <string>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <fstream>

namespace SMTLIBParser {

class ParserManager {
private:
    std::vector<std::shared_ptr<ParserInterface>> parsers;
    
public:
    // 添加解析器
    void addParser(std::shared_ptr<ParserInterface> parser) {
        parsers.push_back(parser);
    }
    
    // 初始化所有支持的解析器
    bool initializeParsers() {
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
            

            
            // 尝试添加SMT-Switch解析器
            try {
                addParser(std::make_shared<SMTSwitchParser>());
            } catch (const std::exception& e) {
                std::cerr << "警告: 无法初始化SMT-Switch解析器: " << e.what() << std::endl;
            }
            

            
            return !parsers.empty();
        } catch (const std::exception& e) {
            std::cerr << "初始化解析器时出错: " << e.what() << std::endl;
            return false;
        }
    }
    
    // 测试单个文件的性能
    std::vector<ParseResult> testFile(const std::string& filename) {
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
    
    // 测试多个文件的性能
    void benchmarkFiles(const std::vector<std::string>& filenames) {
        // 准备结果矩阵
        std::vector<std::vector<ParseResult>> all_results;
        
        for (const auto& filename : filenames) {
            std::vector<ParseResult> file_results = testFile(filename);
            all_results.push_back(file_results);
        }
        
        // 生成对比报告
        generateReport(filenames, all_results);
    }
    
    // 生成性能对比报告
    void generateReport(
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
    
    // 获取已加载的解析器数量
    size_t getParserCount() const {
        return parsers.size();
    }
    
    // 列出所有可用的解析器
    void listParsers() const {
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
};

} // namespace SMTLIBParser 