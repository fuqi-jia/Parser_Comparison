/**
 * SOMTParser dumpSMT2 + dual Z3 solve paths, verdict comparison (standalone experiment).
 *
 * Path A: Z3 parse original file -> check_sat (full assertions).
 * Path B: SOMTParser parse original -> dumpSMT2 to temp -> Z3 parse dump -> check_sat.
 *
 * JSON on stdout. "verdict_disagree" is true only for (sat,unsat) or (unsat,sat); unknown
 * on either side does not count as disagreement.
 *
 * Usage: native_z3_dual_path <input.smt2> <solve_timeout_ms>
 */
#include "somtparser/parser.h"
#include <z3++.h>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <unistd.h>

namespace fs = std::filesystem;

static std::string read_all(const std::string& path) {
    std::ifstream f(path);
    if (!f) return {};
    std::ostringstream b;
    b << f.rdbuf();
    return b.str();
}

static void esc_json_str(std::ostream& o, const std::string& s) {
    for (char c : s) {
        switch (c) {
            case '"': o << "\\\""; break;
            case '\\': o << "\\\\"; break;
            case '\n': o << "\\n"; break;
            case '\r': o << "\\r"; break;
            case '\t': o << "\\t"; break;
            default: o << c; break;
        }
    }
}

struct Z3PathResult {
    bool parse_ok = false;
    bool solve_ok = false;
    double parse_ms = 0;
    double solve_ms = 0;
    std::string verdict;  // sat | unsat | unknown | ""
    std::string err;
};

static Z3PathResult z3_solve_file(const std::string& path, unsigned solve_timeout_ms) {
    Z3PathResult r;
    try {
        z3::context ctx;
        z3::solver solver(ctx);
        z3::params p(ctx);
        p.set("timeout", solve_timeout_ms);
        solver.set(p);

        auto t0 = std::chrono::high_resolution_clock::now();
        try {
            z3::expr_vector assertions = ctx.parse_file(path.c_str());
            for (unsigned i = 0; i < assertions.size(); ++i)
                solver.add(assertions[i]);
            r.parse_ok = true;
        } catch (const z3::exception&) {
            std::string content = read_all(path);
            try {
                z3::expr_vector assertions = ctx.parse_string(content.c_str());
                for (unsigned i = 0; i < assertions.size(); ++i)
                    solver.add(assertions[i]);
                r.parse_ok = true;
            } catch (const z3::exception& e2) {
                r.err = std::string("z3_parse: ") + e2.msg();
            }
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        r.parse_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

        if (r.parse_ok) {
            auto t2 = std::chrono::high_resolution_clock::now();
            z3::check_result cr = solver.check();
            auto t3 = std::chrono::high_resolution_clock::now();
            r.solve_ms = std::chrono::duration<double, std::milli>(t3 - t2).count();
            if (cr == z3::sat)
                r.verdict = "sat";
            else if (cr == z3::unsat)
                r.verdict = "unsat";
            else
                r.verdict = "unknown";
            r.solve_ok = true;
        }
    } catch (const z3::exception& e) {
        r.err = std::string("z3: ") + e.msg();
    } catch (const std::exception& e) {
        r.err = std::string("std: ") + e.what();
    } catch (...) {
        r.err = "unknown_error";
    }
    return r;
}

static std::string make_dump_path(const std::string& input_path) {
    fs::path p = fs::absolute(input_path);
    auto hash = std::hash<std::string>{}(p.string());
    fs::path tmp = fs::temp_directory_path();
    std::ostringstream oss;
    oss << "somt_dualpath_" << getpid() << "_" << (hash & 0xffffffffu) << ".smt2";
    return (tmp / oss.str()).string();
}

static bool verdict_disagree(const std::string& a, const std::string& b) {
    return (a == "sat" && b == "unsat") || (a == "unsat" && b == "sat");
}

int main(int argc, char* argv[]) {
    unsigned solve_timeout_ms = 600000;
    if (argc >= 3) {
        try {
            solve_timeout_ms = static_cast<unsigned>(std::stoul(argv[2]));
        } catch (...) {
        }
    }

    if (argc < 2) {
        std::cout << "{\"error\":\"usage: native_z3_dual_path <file.smt2> [solve_timeout_ms]\"}\n";
        return 1;
    }

    const std::string input = argv[1];
    if (!fs::exists(input)) {
        std::cout << "{\"dump_ok\":false,\"error\":\"file_not_found\"}\n";
        return 1;
    }

    std::string dump_path = make_dump_path(input);
    bool dump_ok = false;
    double native_dump_ms = 0;
    std::string dump_err;

    // Path A first (Z3 on original), then native dump for path B, then Z3 on dump.
    Z3PathResult pa = z3_solve_file(input, solve_timeout_ms);

    try {
        auto t0 = std::chrono::high_resolution_clock::now();
        SOMTParser::ParserPtr p = SOMTParser::newParser();
        p->setOption("keep_let", false);
        if (!p->parse(input)) {
            dump_err = "native_parse_failed";
        } else {
            p->dumpSMT2(dump_path);
            dump_ok = fs::exists(dump_path) && fs::file_size(dump_path) > 0;
            if (!dump_ok)
                dump_err = "dump_empty_or_missing";
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        native_dump_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    } catch (const std::exception& e) {
        dump_err = e.what();
        dump_ok = false;
    } catch (...) {
        dump_err = "native_exception";
        dump_ok = false;
    }

    Z3PathResult pb{};
    if (dump_ok)
        pb = z3_solve_file(dump_path, solve_timeout_ms);

    if (fs::exists(dump_path)) {
        std::error_code ec;
        fs::remove(dump_path, ec);
    }

    const bool have_both = pa.solve_ok && pb.solve_ok;
    bool disagree = false;
    if (have_both)
        disagree = verdict_disagree(pa.verdict, pb.verdict);

    std::string status;
    if (!dump_ok)
        status = "dump_fail";
    else if (!pa.solve_ok)
        status = "path_a_incomplete";
    else if (!pb.solve_ok)
        status = "path_b_incomplete";
    else if (disagree)
        status = "verdict_disagree";
    else
        status = "verdict_agree";

    std::ostringstream info;
    info << "path_a=" << pa.verdict << ";path_b=" << pb.verdict;
    if (disagree)
        info << ";sat_unsat_mismatch=1";
    else if (have_both)
        info << ";sat_unsat_mismatch=0";

    std::ostringstream o;
    o << '{';
    o << "\"dump_ok\":" << (dump_ok ? "true" : "false");
    o << ",\"native_dump_ms\":" << native_dump_ms;
    o << ",\"path_a_parse_ok\":" << (pa.parse_ok ? "true" : "false");
    o << ",\"path_a_solve_ok\":" << (pa.solve_ok ? "true" : "false");
    o << ",\"path_a_parse_ms\":" << pa.parse_ms;
    o << ",\"path_a_solve_ms\":" << pa.solve_ms;
    o << ",\"path_a_verdict\":\"";
    esc_json_str(o, pa.verdict);
    o << "\"";
    o << ",\"path_b_parse_ok\":" << (pb.parse_ok ? "true" : "false");
    o << ",\"path_b_solve_ok\":" << (pb.solve_ok ? "true" : "false");
    o << ",\"path_b_parse_ms\":" << pb.parse_ms;
    o << ",\"path_b_solve_ms\":" << pb.solve_ms;
    o << ",\"path_b_verdict\":\"";
    esc_json_str(o, pb.verdict);
    o << "\"";
    o << ",\"verdict_disagree\":" << (disagree ? "true" : "false");
    o << ",\"status\":\"" << status << "\"";
    o << ",\"info\":\"";
    esc_json_str(o, info.str());
    o << "\"";
    std::string err = dump_err;
    if (!pa.err.empty()) {
        if (!err.empty()) err += "; ";
        err += "path_a:" + pa.err;
    }
    if (!pb.err.empty()) {
        if (!err.empty()) err += "; ";
        err += "path_b:" + pb.err;
    }
    if (!err.empty()) {
        o << ",\"error\":\"";
        esc_json_str(o, err);
        o << "\"";
    }
    o << "}\n";
    std::cout << o.str();
    return 0;
}
