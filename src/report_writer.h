#pragma once

#include "benchmark_runner.h"
#include "metrics_collector.h"
#include <string>
#include <map>
#include <vector>

namespace SMTComparison {

class ReportWriter {
public:
    // 聚合 CSV：schema_version 注释 + parser,file,min_ms,median_ms,...
    static void writeAggregatedCsv(
        const std::string& path,
        const std::vector<std::string>& files,
        const std::map<std::string, std::map<std::string, AggregatedMetrics>>& parser_file_metrics,
        const std::string& schema_version = "2"
    );

    static void writeRawJsonl(const std::string& path, const std::vector<RawSample>& samples);

    // 机器信息、commit、编译选项、命令行、repeat/warmup/timeout/seed
    static void writeManifest(
        const std::string& path,
        const BenchmarkOptions& opts,
        const std::string& argv0,
        int argc, char* argv[]
    );
};

} // namespace SMTComparison
