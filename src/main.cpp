#include "smt_parser_comparison.h"
#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <algorithm>

namespace fs = std::filesystem;

void printUsage(const char* progName) {
    std::cout << "用法: " << progName << " <命令> [选项]\n\n";
    std::cout << "命令:\n";
    std::cout << "  list          列出所有可用的解析器\n";
    std::cout << "  benchmark     使用所有解析器对指定文件进行性能测试\n";
    std::cout << "  test          测试单个文件\n";
    std::cout << "  batch         批量测试目录中的所有SMT文件\n\n";
    std::cout << "选项:\n";
    std::cout << "  -f, --file    指定要测试的SMT文件路径 (用于test命令)\n";
    std::cout << "  -d, --dir     指定要批量测试的目录 (用于batch命令)\n";
    std::cout << "  -h, --help    显示此帮助信息\n\n";
    std::cout << "示例:\n";
    std::cout << "  " << progName << " list\n";
    std::cout << "  " << progName << " test --file test.smt2\n";
    std::cout << "  " << progName << " benchmark --file test1.smt2 test2.smt2\n";
    std::cout << "  " << progName << " batch --dir ../benchmarks\n";
}

// 判断文件是否为SMT文件（基于扩展名）
bool isSMTFile(const std::string& filename) {
    size_t pos = filename.find_last_of('.');
    if (pos != std::string::npos) {
        std::string ext = filename.substr(pos);
        return (ext == ".smt" || ext == ".smt2" || ext == ".smtlib");
    }
    return false;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage(argv[0]);
        return 1;
    }

    std::string command = argv[1];
    
    // 创建并初始化解析器管理器
    SMTComparison::ParserManager manager;
    if (!manager.initializeParsers()) {
        std::cerr << "无法初始化解析器管理器" << std::endl;
        return 1;
    }
    
    if (command == "list") {
        // 列出所有可用的解析器
        manager.listParsers();
        return 0;
    }
    else if (command == "test") {
        // 测试单个文件
        if (argc < 4 || (std::string(argv[2]) != "--file" && std::string(argv[2]) != "-f")) {
            std::cerr << "错误: 缺少文件参数\n";
            printUsage(argv[0]);
            return 1;
        }
        
        std::string filename = argv[3];
        manager.testFile(filename);
        return 0;
    }
    else if (command == "benchmark") {
        // 性能测试多个文件
        if (argc < 4 || (std::string(argv[2]) != "--file" && std::string(argv[2]) != "-f")) {
            std::cerr << "错误: 缺少文件参数\n";
            printUsage(argv[0]);
            return 1;
        }
        
        std::vector<std::string> filenames;
        for (int i = 3; i < argc; i++) {
            filenames.push_back(argv[i]);
        }
        
        manager.benchmarkFiles(filenames);
        return 0;
    }
    else if (command == "batch") {
        // 批量测试目录
        if (argc < 4 || (std::string(argv[2]) != "--dir" && std::string(argv[2]) != "-d")) {
            std::cerr << "错误: 缺少目录参数\n";
            printUsage(argv[0]);
            return 1;
        }
        
        std::string dir_path = argv[3];
        std::vector<std::string> filenames;
        
        try {
            // 遍历目录
            for (const auto& entry : fs::recursive_directory_iterator(dir_path)) {
                if (fs::is_regular_file(entry) && isSMTFile(entry.path().string())) {
                    filenames.push_back(entry.path().string());
                }
            }
            
            if (filenames.empty()) {
                std::cerr << "在目录 " << dir_path << " 中未找到SMT文件" << std::endl;
                return 1;
            }
            
            // 按文件名排序
            std::sort(filenames.begin(), filenames.end());
            
            std::cout << "找到 " << filenames.size() << " 个SMT文件，开始测试..." << std::endl;
            manager.benchmarkFiles(filenames);
            return 0;
        }
        catch (const std::exception& e) {
            std::cerr << "处理目录时出错: " << e.what() << std::endl;
            return 1;
        }
    }
    else if (command == "--help" || command == "-h") {
        printUsage(argv[0]);
        return 0;
    }
    else {
        std::cerr << "未知命令: " << command << std::endl;
        printUsage(argv[0]);
        return 1;
    }
}