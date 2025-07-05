#include "smt_parser_comparison.h"

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
                // 子进程被信号终止（如段错误）
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

// ======== NativeParser实现 ========
NativeParser::NativeParser() {
    parser = std::make_shared<ParserWrapper>();
}

ParseResult NativeParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 获取初始内存使用
    size_t initial_memory = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 使用安全解析来处理潜在的段错误
    bool success = false;
    try {
        double parse_time = PerformanceMetrics::measureExecutionTime([&]() {
            success = safeParseFile([this, &filename]() {
                return parser->parse(filename);
            });
        });
        
        // 记录解析结果
        result.success = success;
        result.parse_time = parse_time;
        
        if (success) {
            result.ast_node_count = parser->getASTNodeCount();
            result.memory_usage = PerformanceMetrics::getCurrentMemoryUsage() - initial_memory;
        } else {
            result.errors = parser->getErrors();
        }
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("解析器异常: ") + e.what());
    }
    
    return result;
}

// ======== PySMTParser实现 ========
ParseResult PySMTParser::parse(const std::string& filename) {
    ParseResult result;
    
    // 获取初始内存使用
    size_t initial_memory = PerformanceMetrics::getCurrentMemoryUsage();
    
    // 准备Python命令
    std::string cmd = python_path + " -c \"from pysmt.smtlib.parser import SmtLibParser; "
                    "import time; "
                    "start = time.time(); "
                    "parser = SmtLibParser(); "
                    "try: "
                    "    script = parser.get_script_fname('" + filename + "'); "
                    "    node_count = len(script.commands); "
                    "    print('SUCCESS'); "
                    "    print(time.time() - start); "
                    "    print(node_count); "
                    "except Exception as e: "
                    "    print('ERROR'); "
                    "    print(e); "
                    "\"";
    
    // 使用安全执行
    bool success = false;
    double parse_time = 0;
    try {
        parse_time = PerformanceMetrics::measureExecutionTime([&]() {
            success = safeParseFile([&]() {
                std::string output = exec(cmd);
                std::istringstream stream(output);
                std::string status;
                std::getline(stream, status);
                
                if (status == "SUCCESS") {
                    std::string time_str, nodes_str;
                    std::getline(stream, time_str);
                    std::getline(stream, nodes_str);
                    
                    try {
                        result.parse_time = std::stod(time_str) * 1000; // 转换为毫秒
                        result.ast_node_count = std::stoull(nodes_str);
                    } catch (...) {
                        return false;
                    }
                    return true;
                } else {
                    std::string error_msg;
                    std::getline(stream, error_msg);
                    result.errors.push_back(error_msg);
                    return false;
                }
            });
        });
    } catch (const std::exception& e) {
        result.success = false;
        result.errors.push_back(std::string("解析器异常: ") + e.what());
    }
    
    result.success = success;
    if (success && result.parse_time == 0) {
        result.parse_time = parse_time;  // 使用外部测量时间作为备份
    }
    result.memory_usage = PerformanceMetrics::getCurrentMemoryUsage() - initial_memory;
    
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
ParserWrapper::ParserWrapper() {
    parser = SMTParser::createParser();
}

ParserWrapper::~ParserWrapper() {
    // 清理工作（如果需要）
}

bool ParserWrapper::parse(const std::string& filename) {
    bool success = false;
    
    try {
        success = parser->parseFile(filename.c_str());
        if (!success) {
            // 获取错误信息
            SMTParser::ErrorVec errs = parser->getErrors();
            for (const auto& err : errs) {
                errors.push_back(err);
            }
        }
    } catch (const std::exception& e) {
        errors.push_back(std::string("解析异常: ") + e.what());
        success = false;
    } catch (...) {
        errors.push_back("解析过程中发生未知异常");
        success = false;
    }
    
    return success;
}

} // namespace SMTComparison 