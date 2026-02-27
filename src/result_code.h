#pragma once

#include <string>

namespace SMTComparison {

// 统一结果码：便于统计与论文表格，替代仅 success bool
enum class ResultCode {
    OK,
    PARSE_ERROR,
    TYPE_ERROR,
    UNSUPPORTED,
    TIMEOUT,
    OOM,
    CRASH,
    UNKNOWN
};

inline const char* to_string(ResultCode c) {
    switch (c) {
        case ResultCode::OK:          return "OK";
        case ResultCode::PARSE_ERROR: return "PARSE_ERROR";
        case ResultCode::TYPE_ERROR:  return "TYPE_ERROR";
        case ResultCode::UNSUPPORTED: return "UNSUPPORTED";
        case ResultCode::TIMEOUT:     return "TIMEOUT";
        case ResultCode::OOM:         return "OOM";
        case ResultCode::CRASH:       return "CRASH";
        case ResultCode::UNKNOWN:     return "UNKNOWN";
    }
    return "UNKNOWN";
}

// 建议：在 ParseResult 中增加以下字段（与现有 success/parse_time/memory_usage 并存）
//   ResultCode result_code;
//   int exit_code;           // 外部进程退出码，-1 表示不适用
//   std::string stderr_snippet;  // 截断到约 512 字符
//   size_t peak_rss_kb;      // 子进程峰值 RSS，与 memory_usage 二选一或并存
// 映射规则：
//   外部：exit 124 或 WIFSIGNALED(SIGKILL) -> TIMEOUT；非零 exit + stderr 关键词 -> PARSE_ERROR/TYPE_ERROR/UNSUPPORTED
//   内部：超时异常 -> TIMEOUT；解析异常 -> PARSE_ERROR；其它 -> CRASH
} // namespace SMTComparison
