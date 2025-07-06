#include "smt_parser_comparison.h"
#include "simple_json.h"
#include <filesystem>

namespace SMTComparison {

// 安全执行解析函数的实现，使用子进程隔离潜在的段错误
bool safeExecute(std::function<bool()> parseFunc, int timeoutSeconds) {
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        std::cerr << "无法创建管道" << std::endl;
        return false;
    }
    
    pid_t pid = fork();
    
    if (pid == -1) {
        // fork失败
        std::cerr << "无法创建子进程" << std::endl;
        close(pipefd[0]);
        close(pipefd[1]);
        return false;
    } else if (pid == 0) {
        // 子进程
        close(pipefd[0]); // 关闭读取端
        
        // 设置超时处理
        signal(SIGALRM, [](int sig) { 
            std::cerr << "解析操作超时" << std::endl; 
            exit(MSG_FAILURE); 
        });
        alarm(timeoutSeconds);
        
        // 执行解析操作
        bool result = false;
        try {
            result = parseFunc();
        } catch (const std::exception& e) {
            std::cerr << "解析过程发生异常: " << e.what() << std::endl;
            write(pipefd[1], &MessageType::MSG_FAILURE, sizeof(MessageType));
            close(pipefd[1]);
            exit(MSG_FAILURE);
        } catch (...) {
            std::cerr << "解析过程发生未知异常" << std::endl;
            write(pipefd[1], &MessageType::MSG_FAILURE, sizeof(MessageType));
            close(pipefd[1]);
            exit(MSG_FAILURE);
        }
        
        // 写入结果
        MessageType msg = result ? MSG_SUCCESS : MSG_FAILURE;
        write(pipefd[1], &msg, sizeof(MessageType));
        close(pipefd[1]);
        exit(result ? MSG_SUCCESS : MSG_FAILURE);
    } else {
        // 父进程
        close(pipefd[1]); // 关闭写入端
        
        MessageType result = MSG_CRASH;
        int status;
        
        // 等待子进程完成或超时
        if (waitpid(pid, &status, 0) != -1) {
            if (WIFEXITED(status)) {
                // 子进程正常退出
                read(pipefd[0], &result, sizeof(MessageType));
            } else if (WIFSIGNALED(status)) {
                // 子进程被信号终止（如段错误或可能是exit()调用）
                result = MSG_CRASH;
                std::cerr << "解析器崩溃 (信号 " << WTERMSIG(status) << ")" << std::endl;
            }
        }
        
        close(pipefd[0]);
        return result == MSG_SUCCESS;
    }
    
    return false; // 不会执行到这里
}

// ParserInterface中保护方法的实现
bool ParserInterface::safeParseFile(const std::function<bool()>& parseFunc) {
    return safeExecute(parseFunc);
}

// 执行外部命令并获取输出的帮助函数
std::string exec(const std::string& cmd) {
    std::array<char, 4096> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) {
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

// 获取包装器可执行文件的路径
std::string getWrapperPath() {
    // 首先尝试当前目录
    std::string wrapper = "./smt_parser_wrapper";
    if (std::filesystem::exists(wrapper)) {
        return wrapper;
    }
    
    // 尝试构建目录
    wrapper = "../smt_parser_wrapper";
    if (std::filesystem::exists(wrapper)) {
        return wrapper;
    }
    
    // 尝试相对于源码的路径
    wrapper = "../build/src/smt_parser_wrapper";
    if (std::filesystem::exists(wrapper)) {
        return wrapper;
    }
    
    // 尝试相对于构建目录的路径
    wrapper = "../build/smt_parser_wrapper";
    if (std::filesystem::exists(wrapper)) {
        return wrapper;
    }
    
    // 返回一个默认路径，并依赖系统的PATH环境变量
    return "smt_parser_wrapper";
}

// ======== NativeParser实现 ========
NativeParser::NativeParser() {
    // 不再需要ParserWrapper
}

ParseResult NativeParser::parse(const std::string& filename) {
    ParseResult result;
    
    try {
        // 获取wrapper的路径
        std::string wrapper_path = getWrapperPath();
        
        // 构建调用wrapper的命令
        std::string cmd = wrapper_path + " \"" + filename + "\"";
        
        // 调用外部程序解析文件
        std::string output = exec(cmd);
        
        // 解析JSON输出
        try {
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            
            // 填充结果结构
            result.success = json["success"].getBool();
            result.parse_time = json["parse_time"].getNumber();
            result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
            result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
            
            // 获取错误信息
            if (json["errors"].isArray()) {
                const auto& errors = json["errors"].getArray();
                for (const auto& err : errors) {
                    result.errors.push_back(err.getString());
                }
            }
        } catch (const std::exception& e) {
            result.success = false;
            result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
            result.errors.push_back("原始输出: " + output);
        }
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("执行外部解析器失败: ") + e.what());
    }
    
    return result;
}

// ======== PySMTParser实现 ========
ParseResult PySMTParser::parse(const std::string& filename) {
    ParseResult result;
    
    try {
        // 获取pySMT解析器脚本的路径
        std::filesystem::path current_path = std::filesystem::current_path();
        std::string script_path;
        
        // 尝试多个可能的位置
        std::vector<std::string> possible_paths = {
            (current_path / "external" / "pysmt" / "pysmt_parser.py").string(),
            (current_path / ".." / "external" / "pysmt" / "pysmt_parser.py").string(),
            (std::filesystem::absolute("external/pysmt/pysmt_parser.py")).string(),
            (std::filesystem::absolute("../external/pysmt/pysmt_parser.py")).string()
        };
        
        for (const auto& path : possible_paths) {
            if (std::filesystem::exists(path)) {
                script_path = path;
                break;
            }
        }
        
        if (script_path.empty()) {
            throw std::runtime_error("无法找到pysmt_parser.py脚本");
        }
        
        // 构建Python命令
        std::string cmd = python_path + " \"" + script_path + "\" \"" + filename + "\"";
        
        // 执行Python脚本
        std::string output = exec(cmd);
        
        // 解析JSON输出
        try {
            SimpleJson::Value json = SimpleJson::Parser::parse(output);
            
            // 填充结果结构
            result.success = json["success"].getBool();
            result.parse_time = json["parse_time"].getNumber();
            result.memory_usage = static_cast<size_t>(json["memory_usage"].getNumber());
            result.ast_node_count = static_cast<size_t>(json["ast_node_count"].getNumber());
            
            // 获取错误信息
            if (json["errors"].isArray()) {
                const auto& errors = json["errors"].getArray();
                for (const auto& err : errors) {
                    result.errors.push_back(err.getString());
                }
            }
        } catch (const std::exception& e) {
            result.success = false;
            result.errors.push_back(std::string("解析JSON输出失败: ") + e.what());
            result.errors.push_back("原始输出: " + output);
        }
        
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("执行pySMT解析器失败: ") + e.what());
    }
    
    return result;
}

// ======== ANTLRParser实现 ========
ParseResult ANTLRParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 获取初始内存使用
    size_t initial_memory = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 准备Java命令
    std::string cmd = "java -jar " + parser_path + " " + filename + " 2>&1";
    
    // 使用安全执行
    bool success = false;
    try {
        double parse_time = PerformanceMetrics::measureExecutionTime([&]() {
            success = safeParseFile([&]() {
                std::string output = exec(cmd);
                
                // 解析输出结果
                if (output.find("SUCCESS") != std::string::npos) {
                    // 尝试解析节点数量
                    size_t pos = output.find("Node count:");
                    if (pos != std::string::npos) {
                        std::string count_str = output.substr(pos + 11);
                        try {
                            result.ast_node_count = std::stoull(count_str);
                        } catch (...) {
                            result.ast_node_count = 0;
                        }
                    }
                    return true;
                } else {
                    result.errors.push_back(output);
                    return false;
                }
            });
        });
        
        result.success = success;
        result.parse_time = parse_time;
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("解析器异常: ") + e.what());
    }
    
    result.memory_usage = PerformanceMetrics::getCurrentMemoryUsage() - initial_memory;
    
    return result;
}

// ======== JSMTLIBParser实现 ========
ParseResult JSMTLIBParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 获取初始内存使用
    size_t initial_memory = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 准备Java命令
    std::string cmd = "java -jar " + parser_path + " " + filename + " 2>&1";
    
    // 使用安全执行
    bool success = false;
    try {
        double parse_time = PerformanceMetrics::measureExecutionTime([&]() {
            success = safeParseFile([&]() {
                std::string output = exec(cmd);
                
                // 解析输出结果
                if (output.find("SUCCESS") != std::string::npos || output.find("Parsed successfully") != std::string::npos) {
                    // 尝试解析节点数量
                    size_t pos = output.find("AST nodes:");
                    if (pos != std::string::npos) {
                        std::string count_str = output.substr(pos + 10);
                        try {
                            result.ast_node_count = std::stoull(count_str);
                        } catch (...) {
                            result.ast_node_count = 0;
                        }
                    }
                    return true;
                } else {
                    result.errors.push_back(output);
                    return false;
                }
            });
        });
        
        result.success = success;
        result.parse_time = parse_time;
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("解析器异常: ") + e.what());
    }
    
    result.memory_usage = PerformanceMetrics::getCurrentMemoryUsage() - initial_memory;
    
    return result;
}

// ======== ParserWrapper实现 ========
// ParserWrapper不再需要，因为我们直接调用外部程序

} // namespace SMTComparison 