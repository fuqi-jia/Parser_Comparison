#include "benchmark_runner.h"
#include "result_code.h"
#include <algorithm>
#include <random>

namespace SMTComparison {

static RawSample parseResultToRawSample(const ParseResult& r, const std::string& parser_name,
                                        const std::string& file_path, int run_index) {
    RawSample s;
    s.parser_name = parser_name;
    s.file_path = file_path;
    s.run_index = run_index;
    s.time_ms = r.parse_time;
    s.peak_rss_kb = r.peak_rss_kb > 0 ? r.peak_rss_kb : r.memory_usage;
    s.result_code = r.result_code;
    s.exit_code = r.exit_code;
    s.stderr_snippet = r.stderr_snippet;
    s.raw_ast_nodes = r.ast_node_count;
    return s;
}

std::vector<RawSample> BenchmarkRunner::run(
    const std::vector<std::shared_ptr<ParserInterface>>& parsers,
    const std::vector<std::string>& files,
    const BenchmarkOptions& opts
) {
    std::vector<std::string> file_list = files;
    if (opts.shuffle && opts.seed != 0) {
        std::mt19937 g(opts.seed);
        std::shuffle(file_list.begin(), file_list.end(), g);
    }

    std::vector<RawSample> samples;
    for (const auto& file : file_list) {
        for (const auto& parser : parsers) {
            for (int w = 0; w < opts.warmup; ++w) {
                (void)parser->parse(file);
            }
            for (int r = 0; r < opts.repeat; ++r) {
                ParseResult res;
                try {
                    res = parser->parse(file);
                } catch (const std::exception& e) {
                    res.success = false;
                    res.result_code = ResultCode::CRASH;
                    res.errors.push_back(e.what());
                } catch (...) {
                    res.success = false;
                    res.result_code = ResultCode::CRASH;
                    res.errors.push_back("未知异常");
                }
                samples.push_back(parseResultToRawSample(res, parser->getName(), file, r));
            }
        }
    }
    return samples;
}

} // namespace SMTComparison
