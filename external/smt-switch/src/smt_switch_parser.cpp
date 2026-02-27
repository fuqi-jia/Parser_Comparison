/**
 * smt_switch_parser：使用 smt-switch 的 SmtLibReader 解析 SMT-LIB 文件，输出本对比工具期望的 JSON。
 * 需在 smt-switch-1.0.6 中启用 SMTLIB_READER 与 BUILD_CVC5 后编译，链接 libsmt-switch 与 smt-switch-cvc5。
 *
 * 使用：./smt_switch_parser <file.smt2>
 */
#include "smt.h"
#include "smtlib_reader.h"
#include "cvc5_factory.h"
#include <iostream>
#include <string>
#include <chrono>
#include <sstream>
#include <vector>
#include <unordered_set>
#include <fstream>
#include <cstdio>
#include <unistd.h>

namespace smt {

/** 统计单个 term 的 AST 节点数（按 id 去重） */
static size_t count_term_nodes(const Term& term, std::unordered_set<std::size_t>& visited) {
    if (!term) return 0;
    std::size_t id = term->get_id();
    if (visited.count(id)) return 0;
    visited.insert(id);
    size_t n = 1;
    for (auto it = term->begin(); it != term->end(); ++it) {
        n += count_term_nodes(*it, visited);
    }
    return n;
}

/** 带节点计数的 SmtLibReader */
class CountingSmtLibReader : public SmtLibReader {
public:
    CountingSmtLibReader(SmtSolver& solver, bool strict = false)
        : SmtLibReader(solver, strict), ast_node_count_(0) {}

    void assert_formula(const Term& assertion) override {
        std::unordered_set<std::size_t> visited;
        ast_node_count_ += count_term_nodes(assertion, visited);
        SmtLibReader::assert_formula(assertion);
    }

    size_t get_ast_node_count() const { return ast_node_count_; }

private:
    size_t ast_node_count_;
};

}  // namespace smt

static std::string escape_json(const std::string& s) {
    std::ostringstream o;
    for (char c : s) {
        if (c == '"') o << "\\\"";
        else if (c == '\\') o << "\\\\";
        else if (c == '\n') o << "\\n";
        else if (c == '\r') o << "\\r";
        else if ((unsigned char)c < 32) o << "\\u" << std::hex << (int)(unsigned char)c;
        else o << c;
    }
    return o.str();
}

int main(int argc, char* argv[]) {
    bool success = false;
    double parse_time_ms = 0;
    size_t memory_kb = 0;
    size_t ast_nodes = 0;
    std::vector<std::string> errors;

    if (argc < 2) {
        errors.push_back("Usage: " + std::string(argv[0]) + " <file.smt2>");
        std::cout << "{\"success\":false,\"parse_time\":0,\"memory_usage\":0,\"ast_node_count\":0,\"errors\":[\""
                  << escape_json(errors[0]) << "\"]}" << std::endl;
        return 1;
    }

    std::string file = argv[1];
    smt::SmtSolver solver = smt::Cvc5SolverFactory::create(false);
    smt::CountingSmtLibReader reader(solver, false);

    auto start = std::chrono::steady_clock::now();
    int saved_stdout = -1;
    try {
#ifdef __linux__
        saved_stdout = dup(STDOUT_FILENO);
        (void)freopen("/dev/null", "w", stdout);
#endif
        reader.parse(file);
#ifdef __linux__
        (void)dup2(saved_stdout, STDOUT_FILENO);
        close(saved_stdout);
        saved_stdout = -1;
#endif
        success = true;
        ast_nodes = reader.get_ast_node_count();
    } catch (const SmtException& e) {
#ifdef __linux__
        if (saved_stdout >= 0) { (void)dup2(saved_stdout, STDOUT_FILENO); close(saved_stdout); saved_stdout = -1; }
#endif
        errors.push_back(e.what());
    } catch (const std::exception& e) {
#ifdef __linux__
        if (saved_stdout >= 0) { (void)dup2(saved_stdout, STDOUT_FILENO); close(saved_stdout); saved_stdout = -1; }
#endif
        errors.push_back(e.what());
    } catch (...) {
#ifdef __linux__
        if (saved_stdout >= 0) { (void)dup2(saved_stdout, STDOUT_FILENO); close(saved_stdout); saved_stdout = -1; }
#endif
        errors.push_back("unknown exception");
    }
    auto end = std::chrono::steady_clock::now();
    parse_time_ms = std::chrono::duration<double, std::milli>(end - start).count();

#ifdef __linux__
    std::ifstream status("/proc/self/status");
    std::string line;
    while (status && std::getline(status, line)) {
        if (line.find("VmRSS:") == 0) {
            std::istringstream iss(line);
            std::string label;
            iss >> label >> memory_kb;
            break;
        }
    }
#endif

    std::cout << "{\"success\":" << (success ? "true" : "false")
              << ",\"parse_time\":" << parse_time_ms
              << ",\"memory_usage\":" << memory_kb
              << ",\"ast_node_count\":" << ast_nodes
              << ",\"errors\":[";
    for (size_t i = 0; i < errors.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << "\"" << escape_json(errors[i]) << "\"";
    }
    std::cout << "]}" << std::endl;
    return success ? 0 : 1;
}
