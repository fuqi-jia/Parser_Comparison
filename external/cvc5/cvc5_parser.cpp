/**
 * cvc5_parser: Parse SMT-LIB with cvc5 C API, output JSON for comparison tool.
 * Links libcvc5/libcvc5parser (no binary). Build: see CMakeLists.txt in this dir.
 *
 * Usage: ./cvc5_parser <file.smt2>
 */
#include <cvc5/c/cvc5.h>
#include <cvc5/c/cvc5_parser.h>
#include <iostream>
#include <string>
#include <chrono>
#include <sstream>
#include <vector>
#include <unordered_set>
#include <fstream>
#include <cstdlib>
#include <cstring>
#include <cstddef>
#include <cstdint>

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

/** 递归统计 term 的 AST 节点数（按 id 去重） */
static size_t count_term_nodes(Cvc5Term term, std::unordered_set<uint64_t>& visited) {
    if (!term) return 0;
    uint64_t id = cvc5_term_get_id(term);
    if (visited.count(id)) return 0;
    visited.insert(id);
    size_t n = 1;
    size_t num_children = cvc5_term_get_num_children(term);
    for (size_t i = 0; i < num_children; ++i) {
        Cvc5Term child = cvc5_term_get_child(term, i);
        n += count_term_nodes(child, visited);
    }
    return n;
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

    const char* file = argv[1];
    Cvc5TermManager* tm = cvc5_term_manager_new();
    Cvc5* cvc5 = cvc5_new(tm);
    Cvc5SymbolManager* sm = cvc5_symbol_manager_new(tm);
    Cvc5InputParser* parser = cvc5_parser_new(cvc5, sm);
    if (!parser) {
        errors.push_back("cvc5_parser_new failed");
        cvc5_symbol_manager_delete(sm);
        cvc5_delete(cvc5);
        cvc5_term_manager_delete(tm);
        std::cout << "{\"success\":false,\"parse_time\":0,\"memory_usage\":0,\"ast_node_count\":0,\"errors\":[\""
                  << escape_json(errors[0]) << "\"]}" << std::endl;
        return 1;
    }

    cvc5_parser_set_file_input(parser, CVC5_INPUT_LANGUAGE_SMT_LIB_2_6, file);

    auto start = std::chrono::steady_clock::now();
    const char* error_msg = nullptr;
    while (!cvc5_parser_done(parser)) {
        Cvc5Command cmd = cvc5_parser_next_command(parser, &error_msg);
        if (error_msg && error_msg[0] != '\0') {
            errors.push_back(error_msg);
            success = false;
            break;
        }
        if (!cmd) break;
        const char* out = cvc5_cmd_invoke(cmd, cvc5, sm);
        (void)out;
    }
    if (errors.empty())
        success = cvc5_parser_done(parser);
    auto end = std::chrono::steady_clock::now();
    parse_time_ms = std::chrono::duration<double, std::milli>(end - start).count();

    if (success) {
        size_t n_assertions = 0;
        const Cvc5Term* assertions = cvc5_get_assertions(cvc5, &n_assertions);
        std::unordered_set<uint64_t> visited;
        for (size_t i = 0; i < n_assertions; ++i)
            ast_nodes += count_term_nodes(assertions[i], visited);
        size_t n_terms = 0;
        const Cvc5Term* declared = cvc5_sm_get_declared_terms(sm, &n_terms);
        for (size_t i = 0; i < n_terms; ++i)
            ast_nodes += count_term_nodes(declared[i], visited);
    }

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

    cvc5_parser_delete(parser);
    cvc5_symbol_manager_delete(sm);
    cvc5_delete(cvc5);
    cvc5_term_manager_delete(tm);

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
