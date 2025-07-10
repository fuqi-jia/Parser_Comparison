#include <iostream>
#include <fstream>
#include <chrono>
#include <string>
#include <vector>
#include <sstream>
#include <exception>
#include <memory>
#include <sys/resource.h>
#include <unistd.h>
#include <z3++.h>

// JSON输出辅助类
class JSONOutput {
private:
    std::stringstream ss;
    bool first_field;

public:
    JSONOutput() : first_field(true) {
        ss << "{";
    }

    void add_field(const std::string& name, bool value) {
        if (!first_field) ss << ",";
        ss << "\"" << name << "\":" << (value ? "true" : "false");
        first_field = false;
    }

    void add_field(const std::string& name, double value) {
        if (!first_field) ss << ",";
        ss << "\"" << name << "\":" << value;
        first_field = false;
    }

    void add_field(const std::string& name, int value) {
        if (!first_field) ss << ",";
        ss << "\"" << name << "\":" << value;
        first_field = false;
    }

    void add_field(const std::string& name, size_t value) {
        if (!first_field) ss << ",";
        ss << "\"" << name << "\":" << value;
        first_field = false;
    }

    void add_field(const std::string& name, const std::string& value) {
        if (!first_field) ss << ",";
        ss << "\"" << name << "\":\"" << escape_json(value) << "\"";
        first_field = false;
    }

    void add_array_field(const std::string& name, const std::vector<std::string>& values) {
        if (!first_field) ss << ",";
        ss << "\"" << name << "\":[";
        for (size_t i = 0; i < values.size(); ++i) {
            if (i > 0) ss << ",";
            ss << "\"" << escape_json(values[i]) << "\"";
        }
        ss << "]";
        first_field = false;
    }

    std::string to_string() {
        ss << "}";
        return ss.str();
    }

private:
    std::string escape_json(const std::string& str) {
        std::string result;
        for (char c : str) {
            switch (c) {
                case '"': result += "\\\""; break;
                case '\\': result += "\\\\"; break;
                case '\b': result += "\\b"; break;
                case '\f': result += "\\f"; break;
                case '\n': result += "\\n"; break;
                case '\r': result += "\\r"; break;
                case '\t': result += "\\t"; break;
                default: result += c; break;
            }
        }
        return result;
    }
};

// 内存使用监控类
class MemoryMonitor {
private:
    size_t initial_memory;

public:
    MemoryMonitor() {
        initial_memory = get_current_memory();
    }

    size_t get_current_memory() {
        struct rusage usage;
        if (getrusage(RUSAGE_SELF, &usage) == 0) {
            // Linux下ru_maxrss是KB，macOS下是bytes
            #ifdef __APPLE__
                return usage.ru_maxrss / 1024;
            #else
                return usage.ru_maxrss;
            #endif
        }
        return 0;
    }

    size_t get_memory_diff() {
        size_t current = get_current_memory();
        return (current > initial_memory) ? (current - initial_memory) : 0;
    }
};

// AST节点计数器
class ASTNodeCounter {
public:
    static size_t count_nodes(const z3::expr& expr) {
        try {
            size_t count = 1; // 当前节点

            // 递归计算子表达式的节点数
            for (unsigned i = 0; i < expr.num_args(); ++i) {
                count += count_nodes(expr.arg(i));
            }

            return count;
        } catch (...) {
            return 1; // 出错时返回最小值
        }
    }

    static size_t count_assertions(const z3::solver& solver) {
        try {
            size_t total_nodes = 0;
            z3::expr_vector assertions = solver.assertions();
            
            for (unsigned i = 0; i < assertions.size(); ++i) {
                total_nodes += count_nodes(assertions[i]);
            }
            
            return total_nodes;
        } catch (...) {
            return 1;
        }
    }
};

// SMT解析器结果结构
struct ParseResult {
    bool success;
    double parse_time; // 毫秒
    size_t memory_usage; // KB
    size_t ast_node_count;
    std::vector<std::string> errors;
    std::string parsing_method;

    ParseResult() : success(false), parse_time(0.0), memory_usage(0), ast_node_count(0) {}
};

// Z3 SMT解析器类
class Z3SMTParser {
private:
    z3::context ctx;
    std::unique_ptr<z3::solver> solver;

public:
    Z3SMTParser() : solver(std::make_unique<z3::solver>(ctx)) {}

    ParseResult parse_file(const std::string& filename) {
        ParseResult result;
        MemoryMonitor memory_monitor;
        
        // 开始计时
        auto start_time = std::chrono::high_resolution_clock::now();
        
        try {
            // 检查文件是否存在
            std::ifstream file(filename);
            if (!file.good()) {
                result.errors.push_back("文件不存在: " + filename);
                return result;
            }
            
            // 读取文件内容
            std::string content;
            std::string line;
            while (std::getline(file, line)) {
                content += line + "\n";
            }
            file.close();
            
            // 方法1: 尝试使用parse_smt2_file
            bool parsed = false;
            try {
                z3::expr_vector assertions = ctx.parse_file(filename.c_str());
                
                // 将断言添加到求解器
                for (unsigned i = 0; i < assertions.size(); ++i) {
                    solver->add(assertions[i]);
                }
                
                // 计算节点数
                result.ast_node_count = 0;
                for (unsigned i = 0; i < assertions.size(); ++i) {
                    result.ast_node_count += ASTNodeCounter::count_nodes(assertions[i]);
                }
                
                result.parsing_method = "z3_parse_file";
                parsed = true;
                
            } catch (const z3::exception& e) {
                // 方法2: 尝试使用parse_smt2_string
                try {
                    z3::expr_vector assertions = ctx.parse_string(content.c_str());
                    
                    // 将断言添加到求解器
                    for (unsigned i = 0; i < assertions.size(); ++i) {
                        solver->add(assertions[i]);
                    }
                    
                    // 计算节点数
                    result.ast_node_count = 0;
                    for (unsigned i = 0; i < assertions.size(); ++i) {
                        result.ast_node_count += ASTNodeCounter::count_nodes(assertions[i]);
                    }
                    
                    result.parsing_method = "z3_parse_string";
                    parsed = true;
                    
                } catch (const z3::exception& e2) {
                    // 方法3: 启发式文本分析
                    try {
                        result.ast_node_count = heuristic_count_nodes(content);
                        result.parsing_method = "heuristic_text_analysis";
                        result.errors.push_back("Z3解析失败，使用启发式方法: " + std::string(e.msg()));
                        result.errors.push_back("Z3字符串解析也失败: " + std::string(e2.msg()));
                        parsed = true;
                        
                    } catch (const std::exception& e3) {
                        result.errors.push_back("所有解析方法都失败");
                        result.errors.push_back("Z3文件解析失败: " + std::string(e.msg()));
                        result.errors.push_back("Z3字符串解析失败: " + std::string(e2.msg()));
                        result.errors.push_back("启发式解析失败: " + std::string(e3.what()));
                        return result;
                    }
                }
            }
            
            // 如果通过求解器还没有计算节点数，尝试从求解器获取
            if (result.ast_node_count == 0) {
                result.ast_node_count = ASTNodeCounter::count_assertions(*solver);
                if (result.parsing_method.empty()) {
                    result.parsing_method = "z3_solver_assertions";
                }
            }
            
            // 确保至少有1个节点
            if (result.ast_node_count == 0) {
                result.ast_node_count = std::max(static_cast<size_t>(1), 
                                                count_parentheses(content));
            }
            
            result.success = true;
            
        } catch (const z3::exception& e) {
            result.errors.push_back("Z3异常: " + std::string(e.msg()));
        } catch (const std::exception& e) {
            result.errors.push_back("标准异常: " + std::string(e.what()));
        } catch (...) {
            result.errors.push_back("未知异常");
        }
        
        // 结束计时
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        result.parse_time = duration.count() / 1000.0; // 转换为毫秒
        
        // 计算内存使用
        result.memory_usage = memory_monitor.get_memory_diff();
        
        return result;
    }

private:
    size_t heuristic_count_nodes(const std::string& content) {
        // 启发式节点计数：基于文本分析
        size_t paren_count = count_parentheses(content);
        size_t word_count = count_words(content);
        size_t number_count = count_numbers(content);
        
        // 估算总节点数
        return paren_count + word_count + number_count;
    }
    
    size_t count_parentheses(const std::string& content) {
        size_t count = 0;
        bool in_string = false;
        bool escape_next = false;
        
        for (char c : content) {
            if (escape_next) {
                escape_next = false;
                continue;
            }
            
            if (c == '\\') {
                escape_next = true;
                continue;
            }
            
            if (c == '"') {
                in_string = !in_string;
                continue;
            }
            
            if (!in_string && c == '(') {
                count++;
            }
        }
        
        return count;
    }
    
    size_t count_words(const std::string& content) {
        std::istringstream iss(content);
        std::string word;
        size_t count = 0;
        
        while (iss >> word) {
            // 排除注释和某些符号
            if (!word.empty() && word[0] != ';' && 
                word != "(" && word != ")") {
                count++;
            }
        }
        
        return count;
    }
    
    size_t count_numbers(const std::string& content) {
        size_t count = 0;
        std::istringstream iss(content);
        std::string word;
        
        while (iss >> word) {
            // 简单的数字检测
            if (!word.empty() && (std::isdigit(word[0]) || 
                (word[0] == '-' && word.length() > 1 && std::isdigit(word[1])))) {
                count++;
            }
        }
        
        return count;
    }
};

// 主函数
int main(int argc, char* argv[]) {
    if (argc != 2) {
        JSONOutput json;
        json.add_field("success", false);
        json.add_field("parse_time", 0.0);
        json.add_field("memory_usage", static_cast<size_t>(0));
        json.add_field("ast_node_count", static_cast<size_t>(0));
        
        std::vector<std::string> errors;
        errors.push_back("用法: " + std::string(argv[0]) + " <smt_file>");
        if (argc > 0) {
            std::string args_str = "接收到的参数: ";
            for (int i = 0; i < argc; ++i) {
                if (i > 0) args_str += " ";
                args_str += argv[i];
            }
            errors.push_back(args_str);
        }
        json.add_array_field("errors", errors);
        
        std::cout << json.to_string() << std::endl;
        return 1;
    }
    
    std::string filename = argv[1];
    
    try {
        Z3SMTParser parser;
        ParseResult result = parser.parse_file(filename);
        
        // 输出JSON结果
        JSONOutput json;
        json.add_field("success", result.success);
        json.add_field("parse_time", result.parse_time);
        json.add_field("memory_usage", result.memory_usage);
        json.add_field("ast_node_count", result.ast_node_count);
        json.add_array_field("errors", result.errors);
        
        if (!result.parsing_method.empty()) {
            json.add_field("parsing_method", result.parsing_method);
        }
        
        std::cout << json.to_string() << std::endl;
        
        return result.success ? 0 : 1;
        
    } catch (const std::exception& e) {
        JSONOutput json;
        json.add_field("success", false);
        json.add_field("parse_time", 0.0);
        json.add_field("memory_usage", static_cast<size_t>(0));
        json.add_field("ast_node_count", static_cast<size_t>(0));
        
        std::vector<std::string> errors;
        errors.push_back("程序异常: " + std::string(e.what()));
        json.add_array_field("errors", errors);
        
        std::cout << json.to_string() << std::endl;
        return 1;
    }
}
