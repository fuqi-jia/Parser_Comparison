#pragma once

#include "benchmark_runner.h"
#include <vector>
#include <cmath>
#include <algorithm>

namespace SMTComparison {

struct AggregatedMetrics {
    double min_ms = 0, median_ms = 0, mean_ms = 0, std_ms = 0, p95_ms = 0;
    size_t min_rss_kb = 0, median_rss_kb = 0, mean_rss_kb = 0, std_rss_kb = 0, p95_rss_kb = 0;
    int ok_count = 0, timeout_count = 0, error_count = 0;
};

class MetricsCollector {
public:
    static AggregatedMetrics compute(const std::vector<RawSample>& samples);

private:
    static double median(std::vector<double> v);
    static double p95(std::vector<double> v);
    static double stddev(const std::vector<double>& v, double mean);
};

} // namespace SMTComparison
