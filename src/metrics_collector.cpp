#include "metrics_collector.h"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace SMTComparison {

double MetricsCollector::median(std::vector<double> v) {
    if (v.empty()) return 0;
    size_t n = v.size() / 2;
    std::nth_element(v.begin(), v.begin() + n, v.end());
    if (v.size() % 2 == 0) {
        double a = v[n];
        std::nth_element(v.begin(), v.begin() + static_cast<ptrdiff_t>(n) - 1, v.end());
        return (v[n - 1] + a) / 2.0;
    }
    return v[n];
}

double MetricsCollector::p95(std::vector<double> v) {
    if (v.empty()) return 0;
    size_t idx = static_cast<size_t>(std::ceil(0.95 * v.size()));
    if (idx == 0) idx = 1;
    idx--;
    std::nth_element(v.begin(), v.begin() + static_cast<ptrdiff_t>(idx), v.end());
    return v[idx];
}

double MetricsCollector::stddev(const std::vector<double>& v, double mean) {
    if (v.size() <= 1) return 0;
    double sum = 0;
    for (double x : v) sum += (x - mean) * (x - mean);
    return std::sqrt(sum / (v.size() - 1));
}

AggregatedMetrics MetricsCollector::compute(const std::vector<RawSample>& samples) {
    AggregatedMetrics m;
    if (samples.empty()) return m;

    for (const auto& s : samples) {
        if (s.result_code == ResultCode::OK) m.ok_count++;
        else if (s.result_code == ResultCode::TIMEOUT) m.timeout_count++;
        else m.error_count++;
    }

    std::vector<double> time_ms, rss_kb;
    for (const auto& s : samples) {
        time_ms.push_back(s.time_ms);
        rss_kb.push_back(static_cast<double>(s.peak_rss_kb));
    }

    double sum_time = std::accumulate(time_ms.begin(), time_ms.end(), 0.0);
    double sum_rss = std::accumulate(rss_kb.begin(), rss_kb.end(), 0.0);
    size_t n = time_ms.size();

    m.min_ms = *std::min_element(time_ms.begin(), time_ms.end());
    m.median_ms = median(time_ms);
    m.mean_ms = sum_time / n;
    m.std_ms = stddev(time_ms, m.mean_ms);
    m.p95_ms = p95(time_ms);

    m.min_rss_kb = static_cast<size_t>(*std::min_element(rss_kb.begin(), rss_kb.end()));
    m.median_rss_kb = static_cast<size_t>(median(rss_kb));
    m.mean_rss_kb = static_cast<size_t>(sum_rss / n);
    m.std_rss_kb = static_cast<size_t>(stddev(rss_kb, sum_rss / n));
    m.p95_rss_kb = static_cast<size_t>(p95(rss_kb));

    return m;
}

} // namespace SMTComparison
