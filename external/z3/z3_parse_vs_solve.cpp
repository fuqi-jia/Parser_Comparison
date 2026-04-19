// Z3: wall-clock for parse_file/parse_string+add vs one full solver.check(), same process.
// Usage: z3_parse_vs_solve <file.smt2> [solve_timeout_ms]
// JSON on stdout; exit 0 iff parse succeeded and check completed (sat/unsat/unknown).

#include <z3++.h>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

class JSONOut {
    std::ostringstream ss;
    bool first = true;

    static std::string esc(const std::string& s) {
        std::string r;
        for (char c : s) {
            if (c == '"') r += "\\\"";
            else if (c == '\\') r += "\\\\";
            else if (c == '\n') r += "\\n";
            else r += c;
        }
        return r;
    }

public:
    void field(const char* k, bool v) {
        if (!first) ss << ',';
        first = false;
        ss << '"' << k << "\":" << (v ? "true" : "false");
    }
    void field(const char* k, double v) {
        if (!first) ss << ',';
        first = false;
        ss << '"' << k << "\":" << v;
    }
    void field(const char* k, const std::string& v) {
        if (!first) ss << ',';
        first = false;
        ss << '"' << k << "\":\"" << esc(v) << '"';
    }
    void arr(const char* k, const std::vector<std::string>& v) {
        if (!first) ss << ',';
        first = false;
        ss << '"' << k << "\":[";
        for (size_t i = 0; i < v.size(); ++i) {
            if (i) ss << ',';
            ss << '"' << esc(v[i]) << '"';
        }
        ss << ']';
    }
    std::string str() {
        return std::string("{") + ss.str() + "}";
    }
};

static std::string read_all(const std::string& path) {
    std::ifstream f(path);
    if (!f) return {};
    std::ostringstream b;
    b << f.rdbuf();
    return b.str();
}

int main(int argc, char* argv[]) {
    std::vector<std::string> errs;
    unsigned solve_timeout_ms = 600000; // 10 min default for batch control via wrapper
    if (argc >= 3) {
        try {
            solve_timeout_ms = static_cast<unsigned>(std::stoul(argv[2]));
        } catch (...) {
            errs.push_back("bad solve_timeout_ms");
        }
    }

    if (argc < 2) {
        JSONOut j;
        j.field("parse_ok", false);
        j.field("solve_ok", false);
        j.field("parse_ms", 0.0);
        j.field("solve_ms", 0.0);
        j.field("check_result", "");
        errs.push_back("usage: z3_parse_vs_solve <file.smt2> [solve_timeout_ms]");
        j.arr("errors", errs);
        std::cout << j.str() << std::endl;
        return 1;
    }

    const std::string filename = argv[1];
    std::ifstream test(filename);
    if (!test.good()) {
        JSONOut j;
        j.field("parse_ok", false);
        j.field("solve_ok", false);
        j.field("parse_ms", 0.0);
        j.field("solve_ms", 0.0);
        j.field("check_result", "");
        errs.push_back("file not found: " + filename);
        j.arr("errors", errs);
        std::cout << j.str() << std::endl;
        return 1;
    }
    test.close();

    z3::context ctx;
    z3::solver solver(ctx);
    z3::params p(ctx);
    p.set("timeout", solve_timeout_ms);
    solver.set(p);

    bool parse_ok = false;
    double parse_ms = 0;
    double solve_ms = 0;
    std::string check_result;
    bool check_ran = false;

    try {
        auto t0 = std::chrono::high_resolution_clock::now();
        try {
            z3::expr_vector assertions = ctx.parse_file(filename.c_str());
            for (unsigned i = 0; i < assertions.size(); ++i)
                solver.add(assertions[i]);
            parse_ok = true;
        } catch (const z3::exception& e) {
            (void)e;
            std::string content = read_all(filename);
            try {
                z3::expr_vector assertions = ctx.parse_string(content.c_str());
                for (unsigned i = 0; i < assertions.size(); ++i)
                    solver.add(assertions[i]);
                parse_ok = true;
            } catch (const z3::exception& e2) {
                errs.push_back(std::string("parse_file failed; parse_string failed: ") + e2.msg());
            }
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        parse_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

        if (parse_ok) {
            auto t2 = std::chrono::high_resolution_clock::now();
            z3::check_result cr = solver.check();
            auto t3 = std::chrono::high_resolution_clock::now();
            solve_ms = std::chrono::duration<double, std::milli>(t3 - t2).count();
            if (cr == z3::sat)
                check_result = "sat";
            else if (cr == z3::unsat)
                check_result = "unsat";
            else
                check_result = "unknown";
            check_ran = true;
        }
    } catch (const z3::exception& e) {
        errs.push_back(std::string("z3: ") + e.msg());
    } catch (const std::exception& e) {
        errs.push_back(std::string("std: ") + e.what());
    } catch (...) {
        errs.push_back("unknown error");
    }

    JSONOut j;
    j.field("parse_ok", parse_ok);
    const bool solve_ok = parse_ok && check_ran && errs.empty();
    j.field("solve_ok", solve_ok);
    j.field("parse_ms", parse_ms);
    j.field("solve_ms", check_ran ? solve_ms : 0.0);
    j.field("check_result", check_result);
    if (!errs.empty())
        j.arr("errors", errs);
    std::cout << j.str() << std::endl;
    return solve_ok ? 0 : 1;
}
