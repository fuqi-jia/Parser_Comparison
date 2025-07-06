#include "../SMTParser/include/parser.h"
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

// 测量内存使用的函数
size_t getCurrentMemoryUsage() {
#ifdef _WIN32
    // Windows实现
    return 0;
#else
    // Linux/Unix实现 - 从/proc/self/status读取
    std::ifstream status("/proc/self/status");
    std::string line;
    while (std::getline(status, line)) {
        if (line.find("VmRSS:") != std::string::npos) {
            std::istringstream iss(line);
            std::string label;
            size_t usage;
            std::string unit;
            iss >> label >> usage >> unit;
            return usage; // 返回KB为单位的内存使用量
        }
    }
    return 0; // 如果无法获取信息
#endif
}

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

// 使用fork创建子进程来解析文件，这样即使SMTParser内部调用exit也不会影响主程序
bool parseFileInChildProcess(const std::string& filename, size_t& ast_node_count, std::vector<std::string>& errors) {
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        errors.push_back("无法创建管道");
        return false;
    }
    
    pid_t pid = fork();
    if (pid == -1) {
        errors.push_back("无法创建子进程");
        close(pipefd[0]);
        close(pipefd[1]);
        return false;
    }
    
    if (pid == 0) {
        // 子进程
        close(pipefd[0]); // 关闭读取端
        
        // 捕获stderr输出
        std::string stderr_output;
        {
            StderrCapture stderr_capture;
            stderr_capture.start();
            
            // 尝试解析文件
            bool success = false;
            try {
                SMTParser::ParserPtr parser = SMTParser::newParser();
                success = parser->parse(filename);
                
                if (success) {
                    // 将AST节点数写入管道
                    ast_node_count = parser->getNodeCount();
                    ssize_t bytes_written = write(pipefd[1], &ast_node_count, sizeof(ast_node_count));
                    if (bytes_written != sizeof(ast_node_count)) {
                        exit(1);
                    }
                } else {
                    // 解析失败，获取错误信息
                    std::vector<std::shared_ptr<SMTParser::DAGNode>> assertions = parser->getAssertions();
                    // 作为失败的标志，我们将节点数设为0
                    ast_node_count = 0;
                    size_t error_count = 1; // 至少有一个错误
                    ssize_t bytes_written = write(pipefd[1], &error_count, sizeof(error_count));
                    if (bytes_written != sizeof(error_count)) {
                        exit(1);
                    }
                    
                    // 由于SMTParser可能没有直接提供getErrors方法，我们使用一个默认错误信息
                    std::string error_message = "SMT解析器报告解析失败";
                    size_t err_len = error_message.length();
                    bytes_written = write(pipefd[1], &err_len, sizeof(err_len));
                    if (bytes_written != sizeof(err_len)) {
                        exit(1);
                    }
                    bytes_written = write(pipefd[1], error_message.c_str(), err_len);
                    if (bytes_written != static_cast<ssize_t>(err_len)) {
                        exit(1);
                    }
                }
            } catch (const std::exception& e) {
                // 异常处理
                success = false;
                std::string error = std::string("解析异常: ") + e.what();
                size_t error_count = 1;
                ssize_t bytes_written = write(pipefd[1], &error_count, sizeof(error_count));
                if (bytes_written != sizeof(error_count)) {
                    exit(1);
                }
                
                size_t err_len = error.length();
                bytes_written = write(pipefd[1], &err_len, sizeof(err_len));
                if (bytes_written != sizeof(err_len)) {
                    exit(1);
                }
                bytes_written = write(pipefd[1], error.c_str(), err_len);
                if (bytes_written != static_cast<ssize_t>(err_len)) {
                    exit(1);
                }
            } catch (...) {
                // 未知异常
                success = false;
                std::string error = "解析过程中发生未知异常";
                size_t error_count = 1;
                ssize_t bytes_written = write(pipefd[1], &error_count, sizeof(error_count));
                if (bytes_written != sizeof(error_count)) {
                    exit(1);
                }
                
                size_t err_len = error.length();
                bytes_written = write(pipefd[1], &err_len, sizeof(err_len));
                if (bytes_written != sizeof(err_len)) {
                    exit(1);
                }
                bytes_written = write(pipefd[1], error.c_str(), err_len);
                if (bytes_written != static_cast<ssize_t>(err_len)) {
                    exit(1);
                }
            }
            
            // 获取stderr输出
            stderr_output = stderr_capture.stop();
        }
        
        // 如果有stderr输出，添加到错误信息中
        if (!stderr_output.empty()) {
            size_t stderr_len = stderr_output.length();
            ssize_t bytes_written = write(pipefd[1], &stderr_len, sizeof(stderr_len));
            if (bytes_written != sizeof(stderr_len)) {
                exit(1);
            }
            bytes_written = write(pipefd[1], stderr_output.c_str(), stderr_len);
            if (bytes_written != static_cast<ssize_t>(stderr_len)) {
                exit(1);
            }
        }
        
        close(pipefd[1]);
        exit(0);
    } else {
        // 父进程
        close(pipefd[1]); // 关闭写入端
        
        bool success = false;
        int status;
        
        // 等待子进程结束
        if (waitpid(pid, &status, 0) != -1) {
            if (WIFEXITED(status)) {
                // 子进程正常退出
                int exit_status = WEXITSTATUS(status);
                
                // 读取子进程的结果
                if (exit_status == 0) {
                    // 尝试读取AST节点数
                    if (read(pipefd[0], &ast_node_count, sizeof(ast_node_count)) == sizeof(ast_node_count)) {
                        success = true;
                    }
                } else {
                    // 解析失败，读取错误信息
                    size_t error_count = 0;
                    if (read(pipefd[0], &error_count, sizeof(error_count)) == sizeof(error_count)) {
                        for (size_t i = 0; i < error_count; ++i) {
                            size_t err_len = 0;
                            if (read(pipefd[0], &err_len, sizeof(err_len)) == sizeof(err_len)) {
                                char* err_buf = new char[err_len + 1];
                                if (read(pipefd[0], err_buf, err_len) == static_cast<ssize_t>(err_len)) {
                                    err_buf[err_len] = '\0';
                                    errors.push_back(err_buf);
                                }
                                delete[] err_buf;
                            }
                        }
                    }
                }
            } else if (WIFSIGNALED(status)) {
                // 子进程被信号终止
                errors.push_back("解析器崩溃 (信号 " + std::to_string(WTERMSIG(status)) + ")");
            }
        } else {
            errors.push_back("等待子进程失败");
        }
        
        close(pipefd[0]);
        return success;
    }
    
    return false; // 不会执行到这里
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

    // 记录开始时的内存使用
    size_t memory_before = getCurrentMemoryUsage();
    
    // 记录开始时间
    auto start = std::chrono::high_resolution_clock::now();
    
    // 使用子进程解析文件，以避免exit调用影响主程序
    bool success = false;
    std::vector<std::string> errors;
    size_t ast_node_count = 0;
    
    success = parseFileInChildProcess(filename, ast_node_count, errors);
    
    // 计算解析时间和内存使用
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> parse_time = end - start;
    size_t memory_after = getCurrentMemoryUsage();
    size_t memory_usage = memory_after - memory_before;
    
    // 输出结果（JSON格式方便解析）
    std::cout << "{" << std::endl;
    std::cout << "  \"success\": " << (success ? "true" : "false") << "," << std::endl;
    std::cout << "  \"parse_time\": " << parse_time.count() << "," << std::endl;
    std::cout << "  \"memory_usage\": " << memory_usage << "," << std::endl;
    std::cout << "  \"ast_node_count\": " << ast_node_count << "," << std::endl;
    std::cout << "  \"errors\": [" << std::endl;
    
    for (size_t i = 0; i < errors.size(); ++i) {
        // 需要正确处理JSON中的特殊字符
        std::string escaped_error = errors[i];
        
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
        if (i < errors.size() - 1) {
            std::cout << ",";
        }
        std::cout << std::endl;
    }
    
    std::cout << "  ]" << std::endl;
    std::cout << "}" << std::endl;
    
    return success ? 0 : 3;
} 