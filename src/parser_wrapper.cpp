#include "somtparser/parser.h"
#include <iostream>
#include <string>
#include <chrono>
#include <vector>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#pragma comment(lib, "psapi.lib")
#endif

// 捕获stderr的类
class StderrCapture {
private:
    int old_stderr;
    int pipe_fd[2];
    bool is_capturing;
    
public:
    StderrCapture() : is_capturing(false) {}
    
    bool start() {
        if (is_capturing) return false;
        
        if (pipe(pipe_fd) != 0) {
            return false;
        }
        
        // 保存原始的stderr
        old_stderr = dup(STDERR_FILENO);
        if (old_stderr == -1) {
            close(pipe_fd[0]);
            close(pipe_fd[1]);
            return false;
        }
        
        // 重定向stderr到管道
        if (dup2(pipe_fd[1], STDERR_FILENO) == -1) {
            close(pipe_fd[0]);
            close(pipe_fd[1]);
            dup2(old_stderr, STDERR_FILENO);
            close(old_stderr);
            return false;
        }
        
        is_capturing = true;
        return true;
    }
    
    std::string stop() {
        if (!is_capturing) return "";
        
        // 刷新stderr缓冲区
        fflush(stderr);
        
        // 恢复原始的stderr
        dup2(old_stderr, STDERR_FILENO);
        close(old_stderr);
        
        // 关闭写入端
        close(pipe_fd[1]);
        
        // 从管道读取stderr的输出
        std::string result;
        char buffer[4096];
        ssize_t n;
        
        while ((n = read(pipe_fd[0], buffer, sizeof(buffer)-1)) > 0) {
            buffer[n] = '\0';
            result += buffer;
        }
        
        close(pipe_fd[0]);
        is_capturing = false;
        
        return result;
    }
    
    ~StderrCapture() {
        if (is_capturing) {
            stop();
        }
    }
};

// 改进的内存使用测量
class MemoryMonitor {
private:
    size_t initial_memory;
    
public:
    MemoryMonitor() {
        initial_memory = getCurrentMemoryUsage();
    }
    
    // 获取当前内存使用（KB）
    static size_t getCurrentMemoryUsage() {
#ifdef _WIN32
        // Windows实现 - 使用Windows API
        PROCESS_MEMORY_COUNTERS_EX pmc;
        if (GetProcessMemoryInfo(GetCurrentProcess(), (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
            return pmc.WorkingSetSize / 1024; // 转换为KB
        }
        return 0;
#else
        // Linux/Unix实现 - 使用更准确的方法
        std::ifstream status("/proc/self/status");
        std::string line;
        size_t vmrss = 0, vmhwm = 0;
        
        while (std::getline(status, line)) {
            if (line.find("VmRSS:") != std::string::npos) {
                std::istringstream iss(line);
                std::string label;
                iss >> label >> vmrss;
            } else if (line.find("VmHWM:") != std::string::npos) {
                std::istringstream iss(line);
                std::string label;
                iss >> label >> vmhwm;
            }
        }
        
        // 返回高水位标记（峰值内存使用）
        return std::max(vmrss, vmhwm);
#endif
    }
    
    // 获取解析过程中的内存增量
    size_t getMemoryDelta() {
        size_t current = getCurrentMemoryUsage();
        return (current > initial_memory) ? (current - initial_memory) : 0;
    }
    
    // 获取峰值内存使用
    size_t getPeakMemoryUsage() {
        return getCurrentMemoryUsage();
    }
};

// 在子进程中进行内存监控的解析
struct ParseResult {
    bool success;
    size_t ast_node_count;
    size_t memory_usage;
    size_t peak_memory;
    std::vector<std::string> errors;
};

// 改进的子进程解析函数
bool parseFileInChildProcess(const std::string& filename, ParseResult& result) {
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        result.errors.push_back("无法创建管道");
        return false;
    }
    
    pid_t pid = fork();
    if (pid == -1) {
        result.errors.push_back("无法创建子进程");
        close(pipefd[0]);
        close(pipefd[1]);
        return false;
    }
    
    if (pid == 0) {
        // 子进程 - 在这里进行内存监控
        close(pipefd[0]); // 关闭读取端
        
        // 初始化内存监控
        MemoryMonitor memory_monitor;
        
        // 声明变量
        bool success = false;
        size_t ast_node_count = 0;
        std::string stderr_output;
        
        // 捕获stderr输出
        {
            StderrCapture stderr_capture;
            stderr_capture.start();
            
            // 尝试解析文件
            try {
                SOMTParser::ParserPtr parser = SOMTParser::newParser();
                parser->setOption("keep_let", false);
                success = parser->parse(filename);
                
                if (success) {
                    ast_node_count = parser->getNodeCount();
                }
            } catch (const std::exception& e) {
                success = false;
                stderr_output += "解析异常: " + std::string(e.what()) + "\n";
            } catch (...) {
                success = false;
                stderr_output += "解析过程中发生未知异常\n";
            }
            
            // 获取stderr输出
            stderr_output += stderr_capture.stop();
        }
        
        // 计算内存使用
        size_t memory_delta = memory_monitor.getMemoryDelta();
        size_t peak_memory = memory_monitor.getPeakMemoryUsage();
        
        // 将结果写入管道
        ssize_t bytes_written = 0;
        bytes_written = write(pipefd[1], &success, sizeof(success));
        (void)bytes_written; // 避免unused variable警告
        
        bytes_written = write(pipefd[1], &ast_node_count, sizeof(ast_node_count));
        (void)bytes_written;
        
        bytes_written = write(pipefd[1], &memory_delta, sizeof(memory_delta));
        (void)bytes_written;
        
        bytes_written = write(pipefd[1], &peak_memory, sizeof(peak_memory));
        (void)bytes_written;
        
        // 写入错误信息
        size_t error_len = stderr_output.length();
        bytes_written = write(pipefd[1], &error_len, sizeof(error_len));
        (void)bytes_written;
        
        if (error_len > 0) {
            bytes_written = write(pipefd[1], stderr_output.c_str(), error_len);
            (void)bytes_written;
        }
        
        close(pipefd[1]);
        exit(success ? 0 : 1);
    } else {
        // 父进程
        close(pipefd[1]); // 关闭写入端
        
        int status;
        bool process_success = false;
        
        // 等待子进程结束
        if (waitpid(pid, &status, 0) != -1) {
            if (WIFEXITED(status)) {
                // 子进程正常退出，读取结果
                bool success;
                size_t ast_node_count, memory_delta, peak_memory, error_len;
                
                if (read(pipefd[0], &success, sizeof(success)) == sizeof(success) &&
                    read(pipefd[0], &ast_node_count, sizeof(ast_node_count)) == sizeof(ast_node_count) &&
                    read(pipefd[0], &memory_delta, sizeof(memory_delta)) == sizeof(memory_delta) &&
                    read(pipefd[0], &peak_memory, sizeof(peak_memory)) == sizeof(peak_memory) &&
                    read(pipefd[0], &error_len, sizeof(error_len)) == sizeof(error_len)) {
                    
                    result.success = success;
                    result.ast_node_count = ast_node_count;
                    result.memory_usage = memory_delta;
                    result.peak_memory = peak_memory;
                    
                    // 读取错误信息
                    if (error_len > 0) {
                        char* error_buf = new char[error_len + 1];
                        if (read(pipefd[0], error_buf, error_len) == static_cast<ssize_t>(error_len)) {
                            error_buf[error_len] = '\0';
                            std::string error_str(error_buf);
                            
                            // 按行分割错误信息
                            std::istringstream iss(error_str);
                            std::string line;
                            while (std::getline(iss, line)) {
                                if (!line.empty()) {
                                    result.errors.push_back(line);
                                }
                            }
                        }
                        delete[] error_buf;
                    }
                    
                    process_success = true;
                }
            } else if (WIFSIGNALED(status)) {
                // 子进程被信号终止
                result.errors.push_back("解析器崩溃 (信号 " + std::to_string(WTERMSIG(status)) + ")");
            }
        } else {
            result.errors.push_back("等待子进程失败");
        }
        
        close(pipefd[0]);
        return process_success;
    }
    
    return false;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "用法: " << argv[0] << " <SMT文件路径>" << std::endl;
        return 1;
    }

    std::string filename = argv[1];
    if (!std::filesystem::exists(filename)) {
        std::cerr << "错误: 文件不存在 - " << filename << std::endl;
        return 2;
    }

    // 记录开始时间
    auto start = std::chrono::high_resolution_clock::now();
    
    // 使用子进程解析文件，以避免exit调用影响主程序
    ParseResult result;
    bool success = parseFileInChildProcess(filename, result);
    
    // 计算解析时间
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> parse_time = end - start;
    
    // 输出结果（JSON格式方便解析）
    std::cout << "{" << std::endl;
    std::cout << "  \"success\": " << (result.success ? "true" : "false") << "," << std::endl;
    std::cout << "  \"parse_time\": " << parse_time.count() << "," << std::endl;
    std::cout << "  \"memory_usage\": " << result.memory_usage << "," << std::endl;
    std::cout << "  \"peak_memory\": " << result.peak_memory << "," << std::endl;
    std::cout << "  \"ast_node_count\": " << result.ast_node_count << "," << std::endl;
    std::cout << "  \"errors\": [" << std::endl;
    
    for (size_t i = 0; i < result.errors.size(); ++i) {
        // 需要正确处理JSON中的特殊字符
        std::string escaped_error = result.errors[i];
        
        // 替换特殊字符
        size_t pos = 0;
        while ((pos = escaped_error.find("\"", pos)) != std::string::npos) {
            escaped_error.replace(pos, 1, "\\\"");
            pos += 2;
        }
        
        pos = 0;
        while ((pos = escaped_error.find("\n", pos)) != std::string::npos) {
            escaped_error.replace(pos, 1, "\\n");
            pos += 2;
        }
        
        std::cout << "    \"" << escaped_error << "\"";
        if (i < result.errors.size() - 1) {
            std::cout << ",";
        }
        std::cout << std::endl;
    }
    
    std::cout << "  ]" << std::endl;
    std::cout << "}" << std::endl;
    
    return result.success ? 0 : 3;
} 