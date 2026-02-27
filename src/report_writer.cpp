#include "report_writer.h"
#include "result_code.h"
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <sys/utsname.h>
#include <array>

namespace SMTComparison {

namespace {

std::string escapeJsonString(const std::string& s) {
    std::ostringstream out;
    for (char c : s) {
        if (c == '"') out << "\\\"";
        else if (c == '\\') out << "\\\\";
        else if (c == '\n') out << "\\n";
        else if (c == '\r') out << "\\r";
        else if (static_cast<unsigned char>(c) < 32) out << "\\u" << std::hex << static_cast<int>(c);
        else out << c;
    }
    return out.str();
}

std::string csvEscape(const std::string& s) {
    std::string out;
    out += '"';
    for (char c : s) { if (c == '"') out += "\"\""; else out += c; }
    out += '"';
    return out;
}

std::string getGitCommit() {
    std::array<char, 128> buf;
    std::string cmd = "git rev-parse HEAD 2>/dev/null";
    FILE* p = popen(cmd.c_str(), "r");
    if (!p) return "";
    std::string out;
    while (fgets(buf.data(), buf.size(), p)) out += buf.data();
    pclose(p);
    while (!out.empty() && (out.back() == '\n' || out.back() == '\r')) out.pop_back();
    return out;
}

} // anonymous namespace

void ReportWriter::writeAggregatedCsv(
    const std::string& path,
    const std::vector<std::string>& files,
    const std::map<std::string, std::map<std::string, AggregatedMetrics>>& parser_file_metrics,
    const std::string& schema_version
) {
    std::ofstream out(path);
    if (!out) return;
    out << "# schema_version=" << schema_version << "\n";
    out << "parser,file,min_ms,median_ms,mean_ms,std_ms,p95_ms,min_rss_kb,median_rss_kb,mean_rss_kb,std_rss_kb,p95_rss_kb,ok_count,timeout_count,error_count\n";
    for (const auto& [parser, file_metrics] : parser_file_metrics) {
        for (const auto& [file, m] : file_metrics) {
            out << csvEscape(parser) << "," << csvEscape(file) << ","
                << m.min_ms << "," << m.median_ms << "," << m.mean_ms << "," << m.std_ms << "," << m.p95_ms << ","
                << m.min_rss_kb << "," << m.median_rss_kb << "," << m.mean_rss_kb << "," << m.std_rss_kb << "," << m.p95_rss_kb << ","
                << m.ok_count << "," << m.timeout_count << "," << m.error_count << "\n";
        }
    }
}

void ReportWriter::writeRawJsonl(const std::string& path, const std::vector<RawSample>& samples) {
    std::ofstream out(path);
    if (!out) return;
    for (const auto& s : samples) {
        out << "{\"parser\":\"" << escapeJsonString(s.parser_name)
            << "\",\"file\":\"" << escapeJsonString(s.file_path)
            << "\",\"run_index\":" << s.run_index
            << ",\"time_ms\":" << s.time_ms
            << ",\"peak_rss_kb\":" << s.peak_rss_kb
            << ",\"result_code\":\"" << to_string(s.result_code)
            << "\",\"exit_code\":" << s.exit_code
            << ",\"raw_ast_nodes\":" << s.raw_ast_nodes << "}\n";
    }
}

void ReportWriter::writeManifest(
    const std::string& path,
    const BenchmarkOptions& opts,
    const std::string& argv0,
    int argc, char* argv[]
) {
    std::ofstream out(path);
    if (!out) return;
    struct utsname u;
    if (uname(&u) == 0) {
        out << "{\"machine\":{\"sysname\":\"" << u.sysname << "\",\"release\":\"" << u.release
            << "\",\"version\":\"" << u.version << "\",\"machine\":\"" << u.machine << "\"}";
    } else {
        out << "{\"machine\":null";
    }
    out << ",\"git_commit\":\"" << escapeJsonString(getGitCommit()) << "\"";
    out << ",\"repeat\":" << opts.repeat;
    out << ",\"warmup\":" << opts.warmup;
    out << ",\"timeout_seconds\":" << opts.timeout_seconds;
    out << ",\"include_startup\":" << (opts.include_startup ? "true" : "false");
    out << ",\"seed\":" << opts.seed;
    out << ",\"shuffle\":" << (opts.shuffle ? "true" : "false");
    out << ",\"cli\":[";
    for (int i = 0; i < argc; ++i) {
        if (i) out << ",";
        out << "\"" << escapeJsonString(argv[i]) << "\"";
    }
    out << "]}\n";
}

} // namespace SMTComparison
