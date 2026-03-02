#include "smt_parser_comparison.h"
#include "benchmark_runner.h"
#include "metrics_collector.h"
#include "report_writer.h"
#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <algorithm>
#include <map>
#include <cstdint>

namespace fs = std::filesystem;

void printUsage(const char* progName) {
    std::cout << "用法: " << progName << " <命令> [选项]\n\n";
    std::cout << "命令:\n";
    std::cout << "  list          列出所有可用的解析器\n";
    std::cout << "  benchmark     使用所有解析器对指定文件进行性能测试\n";
    std::cout << "  test          测试单个文件\n";
    std::cout << "  batch         批量测试目录中的所有SMT文件\n\n";
    std::cout << "选项:\n";
    std::cout << "  -f, --file     指定要测试的SMT文件路径 (用于test/benchmark)；也可直接写路径作位置参数\n";
    std::cout << "  -d, --dir      指定要批量测试的目录 (用于batch命令)\n";
    std::cout << "  -p, --parser   指定要使用的解析器名称 (可选)\n";
    std::cout << "  -o, --output   指定输出CSV文件名 (可选)\n";
    std::cout << "  -t, --timeout  设置解析超时时间(秒) (默认: 60秒)\n";
    std::cout << "  --repeat N     每(解析器,文件)重复N次 (默认: 5，论文级)\n";
    std::cout << "  --warmup W     预热次数，不记录 (默认: 1)\n";
    std::cout << "  --raw-out F    原始样本输出路径 (JSONL)\n";
    std::cout << "  --manifest F   环境与配置摘要 (JSON)\n";
    std::cout << "  --shuffle      打乱文件顺序\n";
    std::cout << "  --seed N       随机种子 (配合 --shuffle)\n";
    std::cout << "  -h, --help     显示此帮助信息\n\n";
    std::cout << "示例:\n";
    std::cout << "  " << progName << " list\n";
    std::cout << "  " << progName << " test --file test.smt2\n";
    std::cout << "  " << progName << " test --parser smt-switch path/to/file.smt2\n";
    std::cout << "  " << progName << " benchmark --parser native --file test1.smt2 --timeout 30\n";
    std::cout << "  " << progName << " benchmark --file test1.smt2 test2.smt2\n";
    std::cout << "  " << progName << " batch --dir ../benchmarks --timeout 180\n";
    std::cout << "  " << progName << " batch --parser pysmt --dir test --output my_results.csv --timeout 300\n";
    std::cout << "\n可用解析器名称: native, pysmt, jsmtlib, z3, antlr4, cvc5, smt-switch（部分需配置 external/ 目录）\n";
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
            arg == "--timeout" || arg == "-t" ||
            arg == "--repeat" || arg == "--warmup" || arg == "--raw-out" || arg == "--manifest" ||
            arg == "--shuffle" || arg == "--seed") {
            
            std::string option = (arg.substr(0, 2) == "--") ? arg.substr(2) : arg.substr(1);
            if (args.find(option) == args.end()) {
                if (option == "p") option = "parser";
                if (option == "f") option = "file";
                if (option == "d") option = "dir";
                if (option == "o") option = "output";
                if (option == "t") option = "timeout";
                args[option] = std::vector<std::string>();
            }
            
            if (arg == "--shuffle") {
                args["shuffle"].push_back("1");
                continue;
            }
            
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
    
    int repeat = 5;
    int warmup = 1;
    std::string rawOutPath;
    std::string manifestPath;
    uint32_t seed = 0;
    bool shuffle = false;
    if (args.find("repeat") != args.end() && !args["repeat"].empty()) {
        try { repeat = std::stoi(args["repeat"][0]); if (repeat < 1) repeat = 1; } catch (...) {}
    }
    if (args.find("warmup") != args.end() && !args["warmup"].empty()) {
        try { warmup = std::stoi(args["warmup"][0]); if (warmup < 0) warmup = 0; } catch (...) {}
    }
    if (args.find("raw-out") != args.end() && !args["raw-out"].empty()) rawOutPath = args["raw-out"][0];
    if (args.find("manifest") != args.end() && !args["manifest"].empty()) manifestPath = args["manifest"][0];
    if (args.find("seed") != args.end() && !args["seed"].empty()) {
        try { seed = static_cast<uint32_t>(std::stoul(args["seed"][0])); } catch (...) {}
    }
    if (args.find("shuffle") != args.end() && !args["shuffle"].empty()) shuffle = true;
    
    bool useBenchmarkRunner = (repeat > 1 || warmup > 0 || !rawOutPath.empty() || !manifestPath.empty());
    
    if (command == "list") {
        // 列出所有可用的解析器
        manager.listParsers();
        return 0;
    }
    else if (command == "test") {
        // 文件参数：优先 --file/-f，否则用第一个位置参数（other）
        std::string filename;
        if (args.find("file") != args.end() && !args["file"].empty()) {
            filename = args["file"][0];
        } else if (args.find("other") != args.end() && !args["other"].empty()) {
            filename = args["other"][0];
        }
        if (filename.empty()) {
            std::cerr << "错误: 缺少文件参数。请用 --file <路径> 或直接写文件路径\n";
            printUsage(argv[0]);
            return 1;
        }
        
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
        // 文件参数：优先 --file/-f（可多个），否则用位置参数（other）
        std::vector<std::string> filenames;
        if (args.find("file") != args.end() && !args["file"].empty()) {
            filenames = args["file"];
        } else if (args.find("other") != args.end() && !args["other"].empty()) {
            filenames = args["other"];
        }
        if (filenames.empty()) {
            std::cerr << "错误: 缺少文件参数。请用 --file <路径> 或直接写文件路径\n";
            printUsage(argv[0]);
            return 1;
        }
        
        std::vector<std::shared_ptr<SMTComparison::ParserInterface>> parsers;
        if (!parserName.empty()) {
            auto p = manager.getParserByName(parserName);
            if (!p) { std::cerr << "找不到解析器: " << parserName << std::endl; return 1; }
            parsers.push_back(p);
        } else {
            for (const auto& p : manager.getParsers()) parsers.push_back(p);
        }
        
        if (useBenchmarkRunner) {
            SMTComparison::BenchmarkOptions opts;
            opts.repeat = repeat;
            opts.warmup = warmup;
            opts.timeout_seconds = timeoutSeconds;
            opts.output_csv = outputFilename.empty() ? "parser_benchmark_results.csv" : outputFilename;
            opts.raw_out_path = rawOutPath;
            opts.manifest_path = manifestPath;
            opts.seed = seed;
            opts.shuffle = shuffle;
            auto samples = SMTComparison::BenchmarkRunner().run(parsers, filenames, opts);
            std::map<std::string, std::map<std::string, SMTComparison::AggregatedMetrics>> parser_file_metrics;
            for (const auto& parser : parsers) {
                std::string pname = parser->getName();
                for (const auto& file : filenames) {
                    std::vector<SMTComparison::RawSample> group;
                    for (const auto& s : samples)
                        if (s.parser_name == pname && s.file_path == file) group.push_back(s);
                    parser_file_metrics[pname][file] = SMTComparison::MetricsCollector::compute(group);
                }
            }
            SMTComparison::ReportWriter::writeAggregatedCsv(opts.output_csv, filenames, parser_file_metrics, "2");
            if (!opts.raw_out_path.empty())
                SMTComparison::ReportWriter::writeRawJsonl(opts.raw_out_path, samples);
            if (!opts.manifest_path.empty())
                SMTComparison::ReportWriter::writeManifest(opts.manifest_path, opts, argv[0], argc, argv);
            std::cout << "聚合报告: " << opts.output_csv << std::endl;
            return 0;
        }
        
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
            
            std::vector<std::shared_ptr<SMTComparison::ParserInterface>> parsers;
            if (!parserName.empty()) {
                auto p = manager.getParserByName(parserName);
                if (!p) { std::cerr << "找不到解析器: " << parserName << std::endl; return 1; }
                parsers.push_back(p);
            } else {
                for (const auto& x : manager.getParsers()) parsers.push_back(x);
            }
            
            if (useBenchmarkRunner) {
                SMTComparison::BenchmarkOptions opts;
                opts.repeat = repeat;
                opts.warmup = warmup;
                opts.timeout_seconds = timeoutSeconds;
                opts.output_csv = outputFilename.empty() ? "parser_benchmark_results.csv" : outputFilename;
                opts.raw_out_path = rawOutPath;
                opts.manifest_path = manifestPath;
                opts.seed = seed;
                opts.shuffle = shuffle;
                auto samples = SMTComparison::BenchmarkRunner().run(parsers, filenames, opts);
                std::map<std::string, std::map<std::string, SMTComparison::AggregatedMetrics>> parser_file_metrics;
                for (const auto& parser : parsers) {
                    std::string pname = parser->getName();
                    for (const auto& file : filenames) {
                        std::vector<SMTComparison::RawSample> group;
                        for (const auto& s : samples)
                            if (s.parser_name == pname && s.file_path == file) group.push_back(s);
                        parser_file_metrics[pname][file] = SMTComparison::MetricsCollector::compute(group);
                    }
                }
                SMTComparison::ReportWriter::writeAggregatedCsv(opts.output_csv, filenames, parser_file_metrics, "2");
                if (!opts.raw_out_path.empty())
                    SMTComparison::ReportWriter::writeRawJsonl(opts.raw_out_path, samples);
                if (!opts.manifest_path.empty())
                    SMTComparison::ReportWriter::writeManifest(opts.manifest_path, opts, argv[0], argc, argv);
                std::cout << "聚合报告: " << opts.output_csv << std::endl;
                return 0;
            }
            
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