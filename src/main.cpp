#include "smt_parser_comparison.h"
#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <algorithm>
#include <map>

namespace fs = std::filesystem;

void printUsage(const char* progName) {
    std::cout << "用法: " << progName << " <命令> [选项]\n\n";
    std::cout << "命令:\n";
    std::cout << "  list          列出所有可用的解析器\n";
    std::cout << "  benchmark     使用所有解析器对指定文件进行性能测试\n";
    std::cout << "  test          测试单个文件\n";
    std::cout << "  batch         批量测试目录中的所有SMT文件\n\n";
    std::cout << "选项:\n";
    std::cout << "  -f, --file     指定要测试的SMT文件路径 (用于test命令)\n";
    std::cout << "  -d, --dir      指定要批量测试的目录 (用于batch命令)\n";
    std::cout << "  -p, --parser   指定要使用的解析器名称 (可选)\n";
    std::cout << "  -o, --output   指定输出CSV文件名 (可选)\n";
    std::cout << "  -t, --timeout  设置解析超时时间(秒) (默认: 60秒)\n";
    std::cout << "  -h, --help     显示此帮助信息\n\n";
    std::cout << "示例:\n";
    std::cout << "  " << progName << " list\n";
    std::cout << "  " << progName << " test --file test.smt2\n";
    std::cout << "  " << progName << " test --file test.smt2 --timeout 120\n";
    std::cout << "  " << progName << " benchmark --file test1.smt2 test2.smt2\n";
    std::cout << "  " << progName << " benchmark --parser native --file test1.smt2 --timeout 30\n";
    std::cout << "  " << progName << " batch --dir ../benchmarks --timeout 180\n";
    std::cout << "  " << progName << " batch --parser pysmt --dir test --output my_results.csv --timeout 300\n";
    std::cout << "\n可用解析器名称: native, pysmt, jsmtlib, z3, antlr4\n";
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

// 解析命令行参数
std::map<std::string, std::vector<std::string>> parseArgs(int argc, char* argv[]) {
    std::map<std::string, std::vector<std::string>> args;
    
    // 跳过程序名和命令
    for (int i = 2; i < argc; i++) {
        std::string arg = argv[i];
        
        // 处理选项
        if (arg == "--file" || arg == "-f" ||
            arg == "--dir" || arg == "-d" ||
            arg == "--parser" || arg == "-p" ||
            arg == "--output" || arg == "-o" ||
            arg == "--timeout" || arg == "-t") {
            
            // 提取选项名（不含前缀）
            std::string option = (arg.substr(0, 2) == "--") ? 
                                  arg.substr(2) : 
                                  arg.substr(1);
            
            // 初始化空向量
            if (args.find(option) == args.end()) {
                if(option == "p") option = "parser";
                if(option == "f") option = "file";
                if(option == "d") option = "dir";
                if(option == "o") option = "output";
                if(option == "t") option = "timeout";
                args[option] = std::vector<std::string>();
            }
            
            // 收集选项的参数值
            while (i + 1 < argc && argv[i + 1][0] != '-') {
                args[option].push_back(argv[++i]);
            }
        }
        // 处理帮助选项
        else if (arg == "--help" || arg == "-h") {
            args["help"] = std::vector<std::string>();
        }
        // 处理其他未识别参数
        else {
            if (args.find("other") == args.end()) {
                args["other"] = std::vector<std::string>();
            }
            args["other"].push_back(arg);
        }
    }
    
    return args;
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
    
    // 解析命令行参数
    auto args = parseArgs(argc, argv);
    
    // 获取解析器名称（如果指定）
    std::string parserName;
    if (args.find("parser") != args.end() && !args["parser"].empty()) {
        parserName = args["parser"][0];
    }
    
    // 获取输出文件名（如果指定）
    std::string outputFilename;
    if (args.find("output") != args.end() && !args["output"].empty()) {
        outputFilename = args["output"][0];
    }
    
    // 获取超时时间（如果指定，默认为60秒）
    int timeoutSeconds = 60;
    if (args.find("timeout") != args.end() && !args["timeout"].empty()) {
        try {
            timeoutSeconds = std::stoi(args["timeout"][0]);
            if (timeoutSeconds <= 0) {
                std::cerr << "错误: 超时时间必须为正整数" << std::endl;
                return 1;
            }
            std::cout << "使用自定义超时时间: " << timeoutSeconds << " 秒" << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "错误: 无效的超时时间值: " << args["timeout"][0] << std::endl;
            return 1;
        }
    }
    
    // 设置全局超时值
    SMTComparison::g_timeout_seconds = timeoutSeconds;
    
    if (command == "list") {
        // 列出所有可用的解析器
        manager.listParsers();
        return 0;
    }
    else if (command == "test") {
        // 确保提供了文件参数
        if (args.find("file") == args.end() || args["file"].empty()) {
            std::cerr << "错误: 缺少文件参数\n";
            printUsage(argv[0]);
            return 1;
        }
        
        std::string filename = args["file"][0];
        
        if (!parserName.empty()) {
            // 使用指定的解析器
            try {
                manager.testFileWithParser(filename, parserName);
            } catch (const std::exception& e) {
                std::cerr << "错误: " << e.what() << std::endl;
                return 1;
            }
        } else {
            // 使用所有解析器
            manager.testFile(filename);
        }
        
        return 0;
    }
    else if (command == "benchmark") {
        // 确保提供了文件参数
        if (args.find("file") == args.end() || args["file"].empty()) {
            std::cerr << "错误: 缺少文件参数\n";
            printUsage(argv[0]);
            return 1;
        }
        
        // 使用提供的所有文件
        std::vector<std::string> filenames = args["file"];
        
        if (!parserName.empty()) {
            // 使用指定的解析器进行基准测试
            try {
                if (!outputFilename.empty()) {
                    manager.benchmarkFilesWithParser(filenames, parserName, outputFilename);
                } else {
                    manager.benchmarkFilesWithParser(filenames, parserName);
                }
            } catch (const std::exception& e) {
                std::cerr << "错误: " << e.what() << std::endl;
                return 1;
            }
        } else {
            // 使用所有解析器进行基准测试
            if (!outputFilename.empty()) {
                manager.benchmarkFiles(filenames, outputFilename);
            } else {
                manager.benchmarkFiles(filenames);
            }
        }
        
        return 0;
    }
    else if (command == "batch") {
        // 确保提供了目录参数
        if (args.find("dir") == args.end() || args["dir"].empty()) {
            std::cerr << "错误: 缺少目录参数\n";
            printUsage(argv[0]);
            return 1;
        }
        
        std::string dir_path = args["dir"][0];
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
            
            if (!parserName.empty()) {
                // 使用指定的解析器进行基准测试
                try {
                    if (!outputFilename.empty()) {
                        manager.benchmarkFilesWithParser(filenames, parserName, outputFilename);
                    } else {
                        manager.benchmarkFilesWithParser(filenames, parserName);
                    }
                } catch (const std::exception& e) {
                    std::cerr << "错误: " << e.what() << std::endl;
                    return 1;
                }
            } else {
                // 使用所有解析器进行基准测试
                if (!outputFilename.empty()) {
                    manager.benchmarkFiles(filenames, outputFilename);
                } else {
                    manager.benchmarkFiles(filenames);
                }
            }
            
            return 0;
        }
        catch (const std::exception& e) {
            std::cerr << "处理目录时出错: " << e.what() << std::endl;
            return 1;
        }
    }
    else if (command == "--help" || command == "-h" || args.find("help") != args.end()) {
        printUsage(argv[0]);
        return 0;
    }
    else {
        std::cerr << "未知命令: " << command << std::endl;
        printUsage(argv[0]);
        return 1;
    }
}