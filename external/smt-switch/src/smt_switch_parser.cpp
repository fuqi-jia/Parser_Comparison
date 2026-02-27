/**
 * smt_switch_parser：对 SMT-LIB 文件调用 cvc5 并输出本对比工具期望的 JSON。
 * 不链接 smt-switch（smt-switch 无直接“解析文件”的公开 API），仅调用 cvc5 二进制。
 * 编译：见本目录 CMakeLists.txt 或
 *   c++ -std=c++17 -O2 -o smt_switch_parser smt_switch_parser.cpp
 *
 * 使用：./smt_switch_parser <file.smt2>
 * 环境变量：CVC5_BIN 指定 cvc5 可执行路径（默认自动探测）。
 */
#include <iostream>
#include <string>
#include <chrono>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <array>
#include <vector>
#include <sys/stat.h>
#include <unistd.h>
#include <sys/wait.h>

static std::string find_cvc5() {
    const char* env = std::getenv("CVC5_BIN");
    if (env && env[0] != '\0') return env;
#ifdef __linux__
    char buf[4096];
    ssize_t n = readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    if (n > 0) {
        buf[n] = '\0';
        std::string path(buf);
        size_t pos = path.find_last_of("/\\");
        if (pos != std::string::npos) {
            std::string dir = path.substr(0, pos);
            std::string candidates[] = {
                dir + "/../cvc5/cvc5-Linux-x86_64-libcxx-static/bin/cvc5",
                dir + "/../cvc5/bin/cvc5",
                dir + "/../../cvc5/cvc5-Linux-x86_64-libcxx-static/bin/cvc5",
                dir + "/../../cvc5/bin/cvc5"
            };
            for (const auto& c : candidates) {
                struct stat st;
                if (stat(c.c_str(), &st) == 0 && (st.st_mode & S_IXUSR)) return c;
            }
        }
    }
#endif
    return "cvc5";
}

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
    std::string cvc5_bin = find_cvc5();
    std::string cmd = cvc5_bin + " \"" + file + "\" 2>&1";

    auto start = std::chrono::steady_clock::now();
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        errors.push_back("popen failed");
        std::cout << "{\"success\":false,\"parse_time\":0,\"memory_usage\":0,\"ast_node_count\":0,\"errors\":[\""
                  << escape_json(errors[0]) << "\"]}" << std::endl;
        return 1;
    }
    std::string out;
    std::array<char, 4096> buf;
    while (fgets(buf.data(), buf.size(), pipe)) out += buf.data();
    int status = pclose(pipe);
    auto end = std::chrono::steady_clock::now();
    parse_time_ms = std::chrono::duration<double, std::milli>(end - start).count();

    success = (WIFEXITED(status) && WEXITSTATUS(status) == 0);
    if (!success && !out.empty()) {
        std::istringstream iss(out);
        std::string line;
        while (std::getline(iss, line))
            if (!line.empty()) errors.push_back(line);
    }
    if (errors.empty() && !success)
        errors.push_back("cvc5 exited with code " + std::to_string(WIFEXITED(status) ? WEXITSTATUS(status) : -1));

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
