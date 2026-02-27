#pragma once

#include <string>

namespace SMTComparison {

// 子进程执行结果：用于统一外部解析器的执行、超时与资源采集
struct ProcessRunResult {
    bool timed_out = false;
    int exit_code = -1;
    int term_signal = 0;       // 0 表示正常退出
    std::string stdout_output;
    std::string stderr_output; // 建议截断到 512 字符
    double wall_time_ms = 0;
    size_t peak_rss_kb = 0;    // 子进程 VmHWM（Linux /proc/<pid>/status）
};

// 执行外部命令：超时则 kill 子进程并设置 timed_out=true
// Linux/WSL：fork+exec，非阻塞读 stdout/stderr，轮询 /proc/<pid>/status 取 VmHWM
class ProcessRunner {
public:
    static ProcessRunResult run(const std::string& cmd, int timeout_sec);
};

} // namespace SMTComparison
