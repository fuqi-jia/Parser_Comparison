#pragma once

#include "smt_parser_comparison.h"
#include "result_code.h"
#include <vector>
#include <string>
#include <memory>
#include <cstdint>

namespace SMTComparison {

struct BenchmarkOptions {
    int repeat = 5;
    int warmup = 1;
    int timeout_seconds = 60;
    bool include_startup = true;
    enum class Isolate { Process, Inprocess } isolate = Isolate::Process;
    std::string raw_out_path;
    std::string manifest_path;
    std::string output_csv;
    uint32_t seed = 0;
    bool shuffle = false;
};

struct RawSample {
    std::string parser_name;
    std::string file_path;
    int run_index = 0;
    double time_ms = 0;
    size_t peak_rss_kb = 0;
    ResultCode result_code = ResultCode::UNKNOWN;
    int exit_code = -1;
    std::string stderr_snippet;
    size_t raw_ast_nodes = 0;
    size_t unique_ast_nodes = 0;  // 0 可表示 N/A
};

// 驱动 repeat/warmup，收集 RawSample；不依赖 ParserManager 内部结构，仅需 parser->parse() 与结果映射
class BenchmarkRunner {
public:
    std::vector<RawSample> run(
        const std::vector<std::shared_ptr<ParserInterface>>& parsers,
        const std::vector<std::string>& files,
        const BenchmarkOptions& opts
    );
};

} // namespace SMTComparison
