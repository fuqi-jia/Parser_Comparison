#include "smt_parser_comparison.h"
#include <iomanip>
#include <fstream>

namespace SMTComparison {

bool ParserManager::initializeParsers() {
    bool success = true;
    
    try {
        // 添加原生解析器
        addParser(std::make_shared<NativeParser>());
        
        // 尝试添加pySMT解析器
        try {
            addParser(std::make_shared<PySMTParser>());
        } catch (const std::exception& e) {
            std::cerr << "无法初始化pySMT解析器: " << e.what() << std::endl;
        }
        

        
        // 添加jSMTLIB解析器
        addParser(std::make_shared<JSMTLIBParser>());
        
        // 尝试添加Z3解析器
        try {
            addParser(std::make_shared<Z3Parser>());
        } catch (const std::exception& e) {
            std::cerr << "警告: 无法初始化Z3解析器: " << e.what() << std::endl;
        }
        

        

    } catch (const std::exception& e) {
        std::cerr << "初始化解析器时出错: " << e.what() << std::endl;
        success = false;
    }
    
    return success && !parsers.empty();
}

std::vector<ParseResult> ParserManager::testFile(const std::string& filename) {
    std::vector<ParseResult> results;
    
    for (auto& parser : parsers) {
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
        
        results.push_back(result);
    }
    
    return results;
}

void ParserManager::benchmarkFiles(const std::vector<std::string>& filenames) {
    // 存储所有文件的结果
    std::vector<std::vector<ParseResult>> all_results;
    
    // 对每个文件执行测试
    for (const auto& filename : filenames) {
        all_results.push_back(testFile(filename));
    }
    
    // 生成报告
    generateReport(filenames, all_results);
}

void ParserManager::generateReport(
    const std::vector<std::string>& filenames,
    const std::vector<std::vector<ParseResult>>& all_results
) {
    // 确保有解析器和结果
    if (parsers.empty() || all_results.empty()) {
        return;
    }
    
    // 创建CSV文件
    std::ofstream report("parser_comparison_report.csv");
    if (!report) {
        std::cerr << "无法创建报告文件" << std::endl;
        return;
    }
    
    // 写入CSV头
    report << "文件名,";
    for (auto& parser : parsers) {
        report << parser->getName() << "_时间(ms),";
        report << parser->getName() << "_内存(KB),";
        report << parser->getName() << "_节点数,";
        report << parser->getName() << "_成功,";
    }
    report << std::endl;
    
    // 计算统计信息
    std::vector<size_t> success_count(parsers.size(), 0);
    std::vector<double> total_time(parsers.size(), 0);
    std::vector<size_t> total_memory(parsers.size(), 0);
    std::vector<size_t> total_nodes(parsers.size(), 0);
    
    // 写入每个文件的结果
    for (size_t i = 0; i < filenames.size(); ++i) {
        std::string abs_filename = std::filesystem::absolute(filenames[i]).string();
        report << abs_filename << ",";
        
        for (size_t j = 0; j < parsers.size(); ++j) {
            if (i < all_results.size() && j < all_results[i].size()) {
                const auto& result = all_results[i][j];
                
                report << result.parse_time << ",";
                report << result.memory_usage << ",";
                report << result.ast_node_count << ",";
                report << (result.success ? "1" : "0") << ",";
                
                // 更新统计信息
                if (result.success) {
                    success_count[j]++;
                    total_time[j] += result.parse_time;
                    total_memory[j] += result.memory_usage;
                    total_nodes[j] += result.ast_node_count;
                }
            } else {
                report << ",,,,";
            }
        }
        report << std::endl;
    }
    
    // 写入汇总统计
    report << "平均值,";
    for (size_t j = 0; j < parsers.size(); ++j) {
        double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count[j]) / filenames.size() * 100.0);
        double avg_time = success_count[j] > 0 ? (total_time[j] / success_count[j]) : 0;
        double avg_memory = success_count[j] > 0 ? (static_cast<double>(total_memory[j]) / success_count[j]) : 0;
        double avg_nodes = success_count[j] > 0 ? (static_cast<double>(total_nodes[j]) / success_count[j]) : 0;
        
        report << avg_time << ",";
        report << avg_memory << ",";
        report << avg_nodes << ",";
        report << success_rate << "%,";
    }
    report << std::endl;
    
    std::cout << "生成报告: parser_comparison_report.csv" << std::endl;
    
    // 输出控制台摘要
    std::cout << "\n===== 测试摘要 =====" << std::endl;
    std::cout << "总文件数: " << filenames.size() << std::endl;
    
    std::cout << "\n解析器成功率:" << std::endl;
    for (size_t j = 0; j < parsers.size(); ++j) {
        double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count[j]) / filenames.size() * 100.0);
        std::cout << "  " << parsers[j]->getName() << ": " 
                 << std::fixed << std::setprecision(2) << success_rate << "% ("
                 << success_count[j] << "/" << filenames.size() << ")" << std::endl;
    }
    
    std::cout << "\n平均解析时间(毫秒):" << std::endl;
    for (size_t j = 0; j < parsers.size(); ++j) {
        double avg_time = success_count[j] > 0 ? (total_time[j] / success_count[j]) : 0;
        std::cout << "  " << parsers[j]->getName() << ": " 
                 << std::fixed << std::setprecision(2) << avg_time << std::endl;
    }
    
    std::cout << "\n平均内存使用(KB):" << std::endl;
    for (size_t j = 0; j < parsers.size(); ++j) {
        double avg_memory = success_count[j] > 0 ? (static_cast<double>(total_memory[j]) / success_count[j]) : 0;
        std::cout << "  " << parsers[j]->getName() << ": " 
                 << std::fixed << std::setprecision(2) << avg_memory << std::endl;
    }
}

void ParserManager::listParsers() const {
    std::cout << "可用的SMT-LIB解析器:" << std::endl;
    for (const auto& parser : parsers) {
        std::cout << "  - " << parser->getName() << " (版本: " << parser->getVersion()
                  << ", 语言: " << parser->getLanguage() << ")" << std::endl;
        
        std::cout << "    支持的功能: ";
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
                // 查找最有用的错误信息
                std::string primaryError = result.errors[0];
                for (const auto& error : result.errors) {
                    if (error.find("list index out of range") != std::string::npos) {
                        primaryError = error;
                        break;
                    }
                    if (error.find("解析文件失败") != std::string::npos) {
                        primaryError = error;
                        break;
                    }
                }
                std::cout << "  错误: " << primaryError << std::endl;
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
    // 存储所有文件的结果
    std::vector<std::vector<ParseResult>> all_results;
    
    // 对每个文件执行测试
    for (const auto& filename : filenames) {
        all_results.push_back(testFile(filename));
    }
    
    // 生成报告
    generateReport(filenames, all_results, outputFilename);
}

// 重载版本：带输出文件名的generateReport
void ParserManager::generateReport(
    const std::vector<std::string>& filenames,
    const std::vector<std::vector<ParseResult>>& all_results,
    const std::string& outputFilename
) {
    // 确保有解析器和结果
    if (parsers.empty() || all_results.empty()) {
        return;
    }
    
    // 创建CSV文件
    std::ofstream report(outputFilename);
    if (!report) {
        std::cerr << "无法创建报告文件: " << outputFilename << std::endl;
        return;
    }
    
    // 写入CSV头
    report << "文件名,";
    for (auto& parser : parsers) {
        report << parser->getName() << "_时间(ms),";
        report << parser->getName() << "_内存(KB),";
        report << parser->getName() << "_节点数,";
        report << parser->getName() << "_成功,";
    }
    report << std::endl;
    
    // 计算统计信息
    std::vector<size_t> success_count(parsers.size(), 0);
    std::vector<double> total_time(parsers.size(), 0);
    std::vector<size_t> total_memory(parsers.size(), 0);
    std::vector<size_t> total_nodes(parsers.size(), 0);
    
    // 写入每个文件的结果
    for (size_t i = 0; i < filenames.size(); ++i) {
        std::string abs_filename = std::filesystem::absolute(filenames[i]).string();
        report << abs_filename << ",";
        
        for (size_t j = 0; j < parsers.size(); ++j) {
            if (i < all_results.size() && j < all_results[i].size()) {
                const auto& result = all_results[i][j];
                
                report << result.parse_time << ",";
                report << result.memory_usage << ",";
                report << result.ast_node_count << ",";
                report << (result.success ? "1" : "0") << ",";
                
                // 更新统计信息
                if (result.success) {
                    success_count[j]++;
                    total_time[j] += result.parse_time;
                    total_memory[j] += result.memory_usage;
                    total_nodes[j] += result.ast_node_count;
                }
            } else {
                report << ",,,,";
            }
        }
        report << std::endl;
    }
    
    // 写入汇总统计
    report << "平均值,";
    for (size_t j = 0; j < parsers.size(); ++j) {
        double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count[j]) / filenames.size() * 100.0);
        double avg_time = success_count[j] > 0 ? (total_time[j] / success_count[j]) : 0;
        double avg_memory = success_count[j] > 0 ? (static_cast<double>(total_memory[j]) / success_count[j]) : 0;
        double avg_nodes = success_count[j] > 0 ? (static_cast<double>(total_nodes[j]) / success_count[j]) : 0;
        
        report << avg_time << ",";
        report << avg_memory << ",";
        report << avg_nodes << ",";
        report << success_rate << "%,";
    }
    report << std::endl;
    
    std::cout << "生成报告: " << outputFilename << std::endl;
    
    // 输出控制台摘要
    std::cout << "\n===== 测试摘要 =====" << std::endl;
    std::cout << "总文件数: " << filenames.size() << std::endl;
    
    std::cout << "\n解析器成功率:" << std::endl;
    for (size_t j = 0; j < parsers.size(); ++j) {
        double success_rate = filenames.empty() ? 0 : (static_cast<double>(success_count[j]) / filenames.size() * 100.0);
        std::cout << "  " << parsers[j]->getName() << ": " 
                 << std::fixed << std::setprecision(2) << success_rate << "% ("
                 << success_count[j] << "/" << filenames.size() << ")" << std::endl;
    }
    
    std::cout << "\n平均解析时间(毫秒):" << std::endl;
    for (size_t j = 0; j < parsers.size(); ++j) {
        double avg_time = success_count[j] > 0 ? (total_time[j] / success_count[j]) : 0;
        std::cout << "  " << parsers[j]->getName() << ": " 
                 << std::fixed << std::setprecision(2) << avg_time << std::endl;
    }
    
    std::cout << "\n平均内存使用(KB):" << std::endl;
    for (size_t j = 0; j < parsers.size(); ++j) {
        double avg_memory = success_count[j] > 0 ? (static_cast<double>(total_memory[j]) / success_count[j]) : 0;
        std::cout << "  " << parsers[j]->getName() << ": " 
                 << std::fixed << std::setprecision(2) << avg_memory << std::endl;
    }
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
                // 查找最有用的错误信息
                std::string primaryError = result.errors[0];
                for (const auto& error : result.errors) {
                    if (error.find("list index out of range") != std::string::npos) {
                        primaryError = error;
                        break;
                    }
                    if (error.find("解析文件失败") != std::string::npos) {
                        primaryError = error;
                        break;
                    }
                }
                std::cout << "  错误: " << primaryError << std::endl;
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