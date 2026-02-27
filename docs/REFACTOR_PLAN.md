# Parser_Comparison 论文级 Benchmark 重构计划

## 一、一致性检查（README vs 代码）

### 1.1 当前状态

| 来源 | 解析器列表 | 说明 |
|------|------------|------|
| **main.cpp printUsage()** | native, pysmt, jsmtlib, z3, antlr4 | CLI 提示的 5 个名称 |
| **smt_parser_comparison.cpp initializeParsers()** | NativeParser, PySMTParser, JSMTLIBParser, Z3Parser, ANTLR4Parser | 实际注册的 5 个（与 CLI 一致） |
| **README 支持的解析器** | 原生、pySMT、ANTLR、jSMTLIB、**SWI-Prolog** | README 多写了 SWI-Prolog，代码未集成 |
| **README external 目录** | antlr/, jsmtlib/, swipl/ | 与实际目录名不一致 |
| **实际 external/** | antlr4_parser/, jsmtlib/, pysmt/, z3/, prolog-smtlib/ | 无 swipl 包装器 |

**parser_manager.h (SMTLIBParser 命名空间)** 引用了 SMTSwitchParser，但 **CMakeLists.txt 只编译 main.cpp + smt_parser_comparison.cpp**，未使用 parser_manager.cpp/parser_manager.h，故 SMTSwitchParser 为死代码，可忽略或后续统一清理。

### 1.2 统一方案

- **支持列表与命名（以代码为准）**  
  - **native** — 本仓库 SMTParser（C++ wrapper 子进程）  
  - **pysmt** — pySMT（Python，external/pysmt）  
  - **jsmtlib** — jSMTLIB（Java，external/jsmtlib）  
  - **z3** — Z3 前端解析（C++ 可执行，external/z3）  
  - **antlr4** — ANTLR4 SMT-LIB 语法（Java，external/antlr4_parser）  

- **可选/扩展解析器（README 写清，代码可选实现）**  
  - **swipl** — SWI-Prolog SMT-LIB 2.6（external/prolog-smtlib，需包装脚本 + 检测 `swipl`）  
  - **haskell** — Haskell smt-lib 库（external/haskell-0.0.2，需 GHC + cabal 编译）  
  - **ocaml** — 已不再维护，仅文档说明“未集成”  

- **external/ 目录规范**  
  - `external/<parser_id>/` 与 parserName 一致或明确映射（见 README 表）。  
  - 检测方式：每个 ExternalParser 在构造时检查可执行/脚本是否存在（如 antlr4 检查 jar 或 run 脚本），失败则 try-add 时跳过并警告。  

- **README 修改**  
  - 列出上述 5 个已支持 + 可选 swipl/haskell，并注明“可选”；  
  - external 布局表使用实际目录名：antlr4_parser, jsmtlib, pysmt, z3, prolog-smtlib；  
  - 说明 parser 名称与真实工具对应关系及检测方式。  

---

## 二、分步骤改动计划（按 commit 拆分）

### Commit 1：一致性清理与文档（低风险）
- **动机**：统一命名与文档，避免读者/审稿人困惑。  
- **内容**：  
  - 更新 README：解析器列表、external 布局、parserName 与工具对应关系、检测方式；  
  - 在 printUsage() 中保持「可用解析器: native, pysmt, jsmtlib, z3, antlr4」，并注明“部分解析器需 external 已配置”。  
- **风险**：无行为变化，仅文档与提示。

### Commit 2：结果码与超时统一（P0，核心）
- **动机**：所有解析器统一结果码与超时语义，便于统计与论文表格。  
- **内容**：  
  - 引入 `ResultCode` 枚举：OK, PARSE_ERROR, TYPE_ERROR, UNSUPPORTED, TIMEOUT, OOM, CRASH, UNKNOWN；  
  - `ParseResult` 增加 `result_code`、可选 `exit_code`、`stderr_snippet`（截断，如 512 字符）；  
  - 外部解析器：超时时统一识别 exit 124 或 SIGTERM/SIGKILL，赋 TIMEOUT；捕获 stderr 写入 `stderr_snippet`；  
  - 内部/native：异常映射到 PARSE_ERROR/TYPE_ERROR/CRASH 等；  
  - 所有 TIMEOUT 路径确保子进程被 kill（当前已用 `timeout` 命令，保留并明确文档化）。  
- **风险**：需在各 parser 的 parse() 返回处填充 result_code，并统一异常到 result_code 的映射。

### Commit 3：ProcessRunner 模块（P0）
- **动机**：统一外部命令执行、超时、stdout/stderr 分离、子进程 peak RSS 采集。  
- **内容**：  
  - 新增 `process_runner.h/.cpp`：`ProcessRunner::run(cmd, timeout_sec)` → 返回结构体：stdout, stderr_snippet, exit_code, signal, peak_rss_kb, timed_out；  
  - Linux/WSL：fork/exec + 非阻塞读 + 轮询 `/proc/<pid>/status` 取 VmHWM 或 wait4/getrusage（RUSAGE_CHILDREN 在 wait 后取 maxrss）；  
  - 超时：alarm 或 timer + kill(SIGKILL) 确保子进程退出；  
  - 现有 ExternalParser::exec() 改为调用 ProcessRunner，并据此填充 ParseResult（time_ms, peak_rss_kb, result_code, stderr_snippet）。  
- **风险**：依赖 Linux /proc 与 wait4；Windows 可留空实现或 #ifdef 返回 0 peak_rss。

### Commit 4：--repeat / --warmup 与统计量（P0）
- **动机**：论文要求“median of five runs”，需可配置重复与预热。  
- **内容**：  
  - CLI：`--repeat N`（默认 5）、`--warmup W`（默认 1）；  
  - BenchmarkRunner（或 ParserManager 内）对每个 (parser, file) 执行：W 次 warmup（不记录），N 次正式跑；  
  - 对 time_ms 与 peak_rss_kb 计算 min/median/mean/std/p95，写入聚合 CSV 与 raw 输出；  
  - 保持现有「单次 run」语义当 repeat=1, warmup=0 时不变。  
- **风险**：benchmark 时间增加 N 倍，需在 README 说明。

### Commit 5：时间/内存口径与 --include-startup / --isolate（P0）
- **动机**：公平比较“是否含启动成本”与“进程隔离”。  
- **内容**：  
  - `--include-startup {true|false}` 默认 true：wall time 包含进程启动；false 时仅对能报告“纯解析时间”的解析器生效（如 native 用 wrapper 内计时）。  
  - `--isolate {process|inprocess}` 默认 process：外部一律子进程；内部 native 建议也默认 fork 子进程跑 wrapper（当前已是），inprocess 则主进程直接调 SMTParser（不 fork）。  
  - 内存：统一报“子进程 peak RSS”（ProcessRunner 提供）；native 在 process 模式下用 wrapper 已报 peak，与其它一致。  
- **风险**：inprocess 下 native 与其它解析器口径不一致（其它仍子进程），需在 README 明确“对比时建议 isolate=process”。

### Commit 6：Raw 输出与 CSV schema 版本（P0）
- **动机**：可复现与后续分析。  
- **内容**：  
  - `--raw-out results.jsonl`（或 raw.csv）：每行一个 (parser, file, run_index, time_ms, peak_rss_kb, result_code, ...)；  
  - 聚合 CSV 第一行或首列增加 schema 版本，如 `# schema_version=2` 或列 `schema_version`；  
  - 现有默认 CSV 保持兼容，仅增加可选版本标识。  
- **风险**：无。

### Commit 7：Manifest 与 batch --shuffle/--seed（P1）
- **动机**：论文方法章节需记录环境与随机性。  
- **内容**：  
  - `--manifest out.json`：输出机器信息（从 /proc 或 uname）、git commit hash、编译 flags（从 build 时写入的宏或文件）、命令行参数、seed、repeat/warmup/timeout 等；  
  - batch：`--shuffle`、`--seed N`，在收集文件列表后 shuffle 再跑（便于报告“顺序随机化”）。  
- **风险**：需在构建时写入版本/编译选项（如 CMake 生成 header 或 json 片段）。

### Commit 8：Feature coverage 框架（P1）
- **动机**：用“feature coverage”替代易误导的“语法覆盖率”。  
- **内容**：  
  - FeatureExtractor：扫描脚本得到 commands 集合（set-logic, declare-fun, assert, check-sat, get-model, …）与 theory/features（BV, FP, Arrays, Strings, Quantifiers, Let, Datatypes, …）；  
  - 输出：每文件一行 feature 集合；可选“parser-level support”表（手填或从结果推断 OK/UNSUPPORTED）；  
  - AST 节点：schema 中区分 raw_ast_nodes 与 unique_nodes（若某 parser 无 hash-consed 则 unique_nodes 填 N/A）。  
- **风险**：feature 列表需与 SMT-LIB 2.6 一致，可先做子集。

### Commit 9：BenchmarkRunner / ReportWriter / MetricsCollector 模块化（P0 结构）
- **动机**：避免 main.cpp 继续膨胀，便于单测与维护。  
- **内容**：  
  - BenchmarkRunner：接收 (parsers, files, opts)，驱动 repeat/warmup、调用 ParserManager 或直接 parser->parse()，收集 RawSample 列表；  
  - MetricsCollector：从 RawSample 计算 min/median/mean/std/p95；  
  - ReportWriter：写聚合 CSV、raw jsonl/csv、manifest；  
  - main.cpp 只做参数解析与调用 BenchmarkRunner + ReportWriter。  
- **风险**：重构时保持现有 CSV 输出格式兼容。

---

## 三、模块接口设计

### 3.1 ProcessRunner（Linux/WSL 优先）

```cpp
// process_runner.h
namespace SMTComparison {

struct ProcessRunResult {
    bool timed_out = false;
    int exit_code = -1;
    int term_signal = 0;       // 0 if exited normally
    std::string stdout_output;
    std::string stderr_output; // 可截断到 512 字符
    double wall_time_ms = 0;
    size_t peak_rss_kb = 0;    // 子进程 VmHWM from /proc/<pid>/status
};

class ProcessRunner {
public:
    // 执行 cmd，超时 timeout_sec 秒；若超时则 kill 子进程并设置 timed_out=true
    static ProcessRunResult run(const std::string& cmd, int timeout_sec);
};

} // namespace SMTComparison
```

- 实现要点：fork + execvp；父进程用 pipe 收 stdout/stderr，另线程或非阻塞读 `/proc/<pid>/status` 取 VmHWM；超时用 kill(pid, SIGKILL)；waitpid 后填 exit_code/term_signal。

### 3.2 BenchmarkRunner

```cpp
// benchmark_runner.h
struct BenchmarkOptions {
    int repeat = 5;
    int warmup = 1;
    int timeout_seconds = 60;
    bool include_startup = true;
    enum class Isolate { Process, Inprocess } isolate = Isolate::Process;
    std::string raw_out_path;   // 空则不写 raw
    std::string manifest_path;  // 空则不写 manifest
    std::string output_csv;     // 聚合 CSV
    uint32_t seed = 0;         // 用于 shuffle
    bool shuffle = false;
};

struct RawSample {
    std::string parser_name;
    std::string file_path;
    int run_index;             // 0..repeat-1
    double time_ms;
    size_t peak_rss_kb;
    ResultCode result_code;
    int exit_code;
    std::string stderr_snippet;
    // 可选
    size_t raw_ast_nodes = 0;
    size_t unique_ast_nodes = 0; // 或 N/A 用 0 表示
};

class BenchmarkRunner {
public:
    // 对 (parsers, files) 执行 repeat+warmup，返回所有 RawSample
    std::vector<RawSample> run(
        const std::vector<std::shared_ptr<ParserInterface>>& parsers,
        const std::vector<std::string>& files,
        const BenchmarkOptions& opts
    );
};
```

### 3.3 MetricsCollector

```cpp
// metrics_collector.h
struct AggregatedMetrics {
    double min_ms, median_ms, mean_ms, std_ms, p95_ms;
    size_t min_rss_kb, median_rss_kb, mean_rss_kb, std_rss_kb, p95_rss_kb;
    int ok_count, timeout_count, error_count; // 按 ResultCode 分类
};

class MetricsCollector {
public:
    // 从同一 (parser, file) 的多次 run 的 RawSample 计算统计量
    static AggregatedMetrics compute(const std::vector<RawSample>& samples);
};
```

### 3.4 ReportWriter

```cpp
// report_writer.h
class ReportWriter {
public:
    static void writeAggregatedCsv(const std::string& path,
        const std::vector<std::string>& files,
        const std::map<std::string, std::map<std::string, AggregatedMetrics>>& parser_file_metrics,
        const std::string& schema_version = "2");

    static void writeRawJsonl(const std::string& path, const std::vector<RawSample>& samples);
    static void writeManifest(const std::string& path, const BenchmarkOptions& opts,
        const std::string& argv0, int argc, char** argv);
};
```

### 3.5 FeatureExtractor（P1）

```cpp
// feature_extractor.h
struct FileFeatures {
    std::set<std::string> commands;   // set-logic, assert, ...
    std::set<std::string> theories;   // BV, FP, LIA, ...
    std::set<std::string> features;   // Quantifiers, Let, Datatypes, ...
};

class FeatureExtractor {
public:
    static FileFeatures extractFromFile(const std::string& path);
};
```

---

## 四、关键实现建议与示例代码

### 4.1 repeat / warmup 循环

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
            auto result = parser->parse(file);  // 需返回或填充 result_code/time/peak_rss
            s.time_ms = result.parse_time;
            s.peak_rss_kb = result.peak_rss_kb;  // 或 peak_memory
            s.result_code = result.result_code;
            samples.push_back(s);
        }
    }
}
```

### 4.2 超时 kill 与 RSS 采集（ProcessRunner 内）

- 使用 `fork()` + `execvp()`，不用 `popen()`，以便获得子进程 pid。  
- 父进程：  
  - 创建 pipe 收 stdout/stderr；  
  - 若使用 `timeout` 命令：则当前行为已能 kill；若自实现超时：在另一线程 sleep(timeout_sec) 后 `kill(pid, SIGKILL)`，主线程 `waitpid` 得到 status。  
- Peak RSS：在子进程存活期间，父进程周期性（如 50ms）读 `/proc/<pid>/status` 取 `VmHWM:`（kB），取最大值；或 Linux 下 `wait4(pid, &status, 0, &ru)` 后 `ru.ru_maxrss` 为 KB（需子进程为直接子进程）。

### 4.3 统计量计算（median / p95）

```cpp
#include <algorithm>
#include <cmath>
static double median(std::vector<double> v) {
    if (v.empty()) return 0;
    size_t n = v.size() / 2;
    std::nth_element(v.begin(), v.begin() + n, v.end());
    if (v.size() % 2 == 0) {
        double a = v[n];
        std::nth_element(v.begin(), v.begin() + n - 1, v.end());
        return (v[n-1] + a) / 2;
    }
    return v[n];
}
static double p95(std::vector<double> v) {
    if (v.empty()) return 0;
    size_t idx = static_cast<size_t>(std::ceil(0.95 * v.size())) - 1;
    std::nth_element(v.begin(), v.begin() + idx, v.end());
    return v[idx];
}
```

### 4.4 稳定 CSV schema（聚合 CSV 示例）

```text
# schema_version=2
# repeat=5,warmup=1,timeout=60,include_startup=true,isolate=process
parser,file,min_ms,median_ms,mean_ms,std_ms,p95_ms,min_rss_kb,median_rss_kb,...,ok_count,timeout_count,...
native,/path/to/a.smt2,12.1,13.0,13.2,0.5,14.1,2048,2100,...,5,0,...
```

- 第一列或前几列固定为 parser, file，便于脚本解析；schema_version 以注释或首列出现一次即可。

### 4.5 ResultCode 枚举与映射

```cpp
enum class ResultCode { OK, PARSE_ERROR, TYPE_ERROR, UNSUPPORTED, TIMEOUT, OOM, CRASH, UNKNOWN };
// 外部：exit 124 或 WIFSIGNALED(SIGKILL) -> TIMEOUT；非零 exit -> 根据 stderr 关键词映射 PARSE_ERROR/TYPE_ERROR/UNSUPPORTED，否则 UNKNOWN
// 内部：catch 超时异常 -> TIMEOUT；解析错误 -> PARSE_ERROR；其它异常 -> CRASH
```

---

## 五、当前仓库最可能导致“不公平/不可复现”的点及修复优先级

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 时间口径不统一：native 用 wrapper 内计时，外部用 popen 全量 wall time | 若 wrapper 未含启动则 native 偏优 | **P0** |
| 内存：仅 native 有子进程 peak（wrapper），其它无子进程 RSS | 内存对比不公平 | **P0** |
| 单次运行、无 repeat/median | 论文要求“median of five runs”无法满足 | **P0** |
| 无 warmup | JVM/Python 首跑偏慢，不公平 | **P0** |
| 超时后子进程依赖 `timeout` 命令 kill，未在代码中显式 kill | 一般已够用，但文档需写明 | **P1** |
| 无结构化结果码，仅 success bool | 无法区分 TIMEOUT/PARSE_ERROR/CRASH | **P0** |
| 外部解析器 stderr 未单独捕获或未写入结果 | 难以复现与诊断 | **P0** |
| CSV 无 schema 版本、无 manifest、无 seed | 复现与审稿困难 | **P0/P1** |
| “语法覆盖率”未定义且可能虚构 | 论文易被质疑 | **P1** → 改为 feature coverage |
| AST 节点未区分 raw vs unique | 不同 parser 不可比 | **P1** |
| batch 顺序固定 | 若有顺序效应则偏倚 | **P2** → --shuffle --seed |
| README 与代码解析器列表不一致 | 用户/审稿人困惑 | **P0** |

---

## 六、实验环境描述（写入 manifest / report）

建议在 `--manifest` 输出的 JSON 中包含（或由 ReportWriter 写入）：

- **machine**: uname -a 或从 /proc/version；可选 CPU/RAM（/proc/cpuinfo, MemTotal）。
- **experiment_note**: "All experiments were conducted on a Linux machine running a 6.6-series kernel. The system is equipped with an AMD Ryzen 9 7940HS processor (8 cores, 16 threads) and 16 GB RAM. SMTParser and all compared solvers were compiled using g++ -O3 under identical settings. Unless otherwise stated, experiments were single-threaded, and runtimes are median of five runs."
- **git_commit**: 运行时可执行 `git rev-parse HEAD` 或读构建时写入的版本文件。
- **build_flags**: 如 "-O3 -DNDEBUG" 等，构建时写入。
- **cli**: 完整命令行。
- **repeat, warmup, timeout, include_startup, isolate, seed**.

以上满足论文方法章节对“可复现实验”的要求。
