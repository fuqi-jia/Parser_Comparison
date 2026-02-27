# 关键实现代码片段

供实现 ProcessRunner、MetricsCollector、repeat/warmup 时参考。C++17，仅头文件或单文件示例。

## 1. 统计量：median / p95 / stddev

```cpp
#include <algorithm>
#include <cmath>
#include <vector>

static double median(std::vector<double> v) {
    if (v.empty()) return 0;
    size_t n = v.size() / 2;
    std::nth_element(v.begin(), v.begin() + n, v.end());
    if (v.size() % 2 == 0) {
        double a = v[n];
        std::nth_element(v.begin(), v.begin() + n - 1, v.end());
        return (v[n - 1] + a) / 2.0;
    }
    return v[n];
}

static double p95(std::vector<double> v) {
    if (v.empty()) return 0;
    size_t idx = static_cast<size_t>(std::ceil(0.95 * v.size()));
    if (idx == 0) idx = 1;
    idx--;
    std::nth_element(v.begin(), v.begin() + idx, v.end());
    return v[idx];
}

static double stddev(const std::vector<double>& v, double mean) {
    if (v.size() <= 1) return 0;
    double sum = 0;
    for (double x : v) sum += (x - mean) * (x - mean);
    return std::sqrt(sum / (v.size() - 1));
}
```

## 2. ProcessRunner::run 思路（Linux）

- 使用 `fork()` + `execvp()`，不用 `popen()`，以便拿到子进程 pid。
- 父进程：
  - 为 stdout/stderr 各建 pipe，重定向子进程的 1/2 到 pipe 写端。
  - 若需 peak RSS：在子进程存活期间周期性（如每 50ms）读 `/proc/<pid>/status`，取 `VmHWM:` 行（单位 kB），取最大值；或 `wait4(pid, &status, 0, &ru)` 后用 `ru.ru_maxrss`（kB）。
  - 超时：单独线程 `sleep(timeout_sec)` 后 `kill(pid, SIGKILL)`；主线程 `waitpid(pid, &status, 0)`，若 WIFSIGNALED 且 WTERMSIG==SIGKILL 则设 `timed_out=true`。
- 读 pipe 时注意缓冲与阻塞；可设 pipe 为 O_NONBLOCK 或用 select/poll 避免死锁。

## 3. 读取子进程 VmHWM（/proc）

```cpp
#include <fstream>
#include <string>
#include <sstream>

size_t getPeakRssKb(pid_t pid) {
    std::string path = "/proc/" + std::to_string(pid) + "/status";
    std::ifstream f(path);
    std::string line;
    size_t vmhwm = 0;
    while (std::getline(f, line)) {
        if (line.compare(0, 6, "VmHWM:") == 0) {
            std::istringstream iss(line.substr(6));
            iss >> vmhwm;
            break;
        }
    }
    return vmhwm;
}
```

## 4. repeat / warmup 循环（伪代码）

```cpp
for (const auto& file : files) {
    for (const auto& parser : parsers) {
        for (int w = 0; w < opts.warmup; ++w)
            parser->parse(file);  // 不记录
        for (int r = 0; r < opts.repeat; ++r) {
            RawSample s;
            s.parser_name = parser->getName();
            s.file_path = file;
            s.run_index = r;
            ParseResult result = parser->parse(file);
            s.time_ms = result.parse_time;
            s.peak_rss_kb = result.peak_rss_kb;  // 或 peak_memory，需在 ParseResult 中统一
            s.result_code = result.result_code;
            s.exit_code = result.exit_code;
            s.stderr_snippet = result.stderr_snippet;
            samples.push_back(s);
        }
    }
}
```

## 5. 聚合 CSV 首行（稳定 schema）

```text
# schema_version=2
# repeat=5,warmup=1,timeout=60,include_startup=true,isolate=process
parser,file,min_ms,median_ms,mean_ms,std_ms,p95_ms,min_rss_kb,median_rss_kb,mean_rss_kb,std_rss_kb,p95_rss_kb,ok_count,timeout_count,error_count
```

## 6. ResultCode 映射（外部进程）

- `WIFEXITED(status) && WEXITSTATUS(status)==124` → TIMEOUT（timeout 命令）
- `WIFSIGNALED(status) && (WTERMSIG(status)==SIGKILL || WTERMSIG(status)==SIGTERM)` 且设置了 timed_out → TIMEOUT
- 非零 exit + stderr 含 "parse error" / "syntax" → PARSE_ERROR
- 非零 exit + stderr 含 "type" / "sort" → TYPE_ERROR
- 非零 exit + stderr 含 "unsupported" / "not supported" → UNSUPPORTED
- 其余非零 exit → UNKNOWN；正常退出且 result.success → OK
