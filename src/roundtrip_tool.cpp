/**
 * Single-engine round-trip for SMTParser (SOMTParser): parse original SMT2,
 * dump linear SMT2 via dumpSMT2(), then parse the dump again with a second
 * Parser instance of the *same* implementation.
 *
 * This is not a cross-parser experiment (that is the main benchmark driver).
 * Even with one engine twice, AST node counts need not match: serialization
 * can change shape (e.g. let removal, canonical printing), so comparing
 * nodes1 vs nodes2 is still meaningful.
 *
 * Heavy work runs in a child process; parent enforces wall-clock timeout.
 * Prints one JSON object on stdout.
 */
#include "somtparser/parser.h"
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <signal.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

namespace fs = std::filesystem;

static void print_json_bool(const char* key, bool v) {
    std::cout << "\"" << key << "\":" << (v ? "true" : "false");
}

static void print_json_num(const char* key, double v) {
    std::cout << "\"" << key << "\":" << v;
}

static void print_json_size(const char* key, size_t v) {
    std::cout << "\"" << key << "\":" << v;
}

static void print_json_str(const char* key, const std::string& s) {
    std::cout << "\"" << key << "\":\"";
    for (char c : s) {
        switch (c) {
            case '"': std::cout << "\\\""; break;
            case '\\': std::cout << "\\\\"; break;
            case '\n': std::cout << "\\n"; break;
            case '\r': std::cout << "\\r"; break;
            case '\t': std::cout << "\\t"; break;
            default: std::cout << c; break;
        }
    }
    std::cout << "\"";
}

static int child_main(const std::string& input_path, const std::string& dump_path) {
    bool ok1 = false, ok2 = false;
    size_t nodes1 = 0, nodes2 = 0;
    std::string err;

    try {
        SOMTParser::ParserPtr p1 = SOMTParser::newParser();
        p1->setOption("keep_let", false);
        ok1 = p1->parse(input_path);
        if (ok1) {
            nodes1 = p1->getNodeCount();
            p1->dumpSMT2(dump_path);
        } else {
            err = "first_parse_failed";
        }

        if (ok1) {
            SOMTParser::ParserPtr p2 = SOMTParser::newParser();
            p2->setOption("keep_let", false);
            ok2 = p2->parse(dump_path);
            if (ok2) {
                nodes2 = p2->getNodeCount();
            } else {
                if (!err.empty()) err += "; ";
                err += "second_parse_failed";
            }
        }
    } catch (const std::exception& e) {
        err = e.what();
        ok1 = false;
        ok2 = false;
    } catch (...) {
        err = "unknown_exception";
        ok1 = false;
        ok2 = false;
    }

    bool match_nodes = ok1 && ok2 && (nodes1 == nodes2);

    std::cout << "{";
    print_json_bool("ok1", ok1);
    std::cout << ",";
    print_json_bool("ok2", ok2);
    std::cout << ",";
    print_json_size("nodes1", nodes1);
    std::cout << ",";
    print_json_size("nodes2", nodes2);
    std::cout << ",";
    print_json_bool("match_nodes", match_nodes);
    std::cout << ",";
    print_json_str("dump_path", dump_path);
    std::cout << ",";
    print_json_str("error", err);
    std::cout << "}\n";
    std::cout.flush();

    return (ok1 && ok2 && match_nodes) ? 0 : 2;
}

static std::string make_dump_path(const std::string& input_path) {
    fs::path p = fs::absolute(input_path);
    auto hash = std::hash<std::string>{}(p.string());
    fs::path tmp = fs::temp_directory_path();
    std::ostringstream oss;
    oss << "somt_roundtrip_" << getpid() << "_" << (hash & 0xffffffffu) << ".smt2";
    return (tmp / oss.str()).string();
}

static void set_mem_limit_mb(unsigned mb) {
    if (mb == 0) return;
    rlimit rl{};
    rl.rlim_cur = static_cast<rlim_t>(mb) * 1024u * 1024u;
    rl.rlim_max = rl.rlim_cur;
    setrlimit(RLIMIT_AS, &rl);
}

int main(int argc, char* argv[]) {
    if (argc < 2 || argc > 4) {
        std::cerr << "用法: " << (argc > 0 ? argv[0] : "roundtrip_tool")
                  << " <input.smt2> [timeout_sec] [memory_limit_mb]\n";
        return 1;
    }

    const std::string input_path = argv[1];
    int timeout_sec = (argc >= 3) ? std::atoi(argv[2]) : 30;
    unsigned mem_mb = (argc >= 4) ? static_cast<unsigned>(std::atoi(argv[3])) : 4096;
    if (timeout_sec <= 0) timeout_sec = 30;

    if (!fs::exists(input_path)) {
        std::cout << "{";
        print_json_bool("ok1", false);
        std::cout << ",";
        print_json_bool("ok2", false);
        std::cout << ",";
        print_json_size("nodes1", 0);
        std::cout << ",";
        print_json_size("nodes2", 0);
        std::cout << ",";
        print_json_bool("match_nodes", false);
        std::cout << ",";
        print_json_str("dump_path", "");
        std::cout << ",";
        print_json_str("error", "file_not_found");
        std::cout << ",";
        print_json_num("wall_ms", 0);
        std::cout << "}\n";
        return 1;
    }

    std::string dump_path = make_dump_path(input_path);

    auto wall0 = std::chrono::high_resolution_clock::now();

    int pipefd[2];
    if (pipe(pipefd) != 0) {
        std::cerr << "pipe failed\n";
        return 1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        std::cerr << "fork failed\n";
        return 1;
    }

    if (pid == 0) {
        close(pipefd[0]);
        if (mem_mb > 0) set_mem_limit_mb(mem_mb);
        // Redirect child's stdout to pipe; stderr stays for crashes
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        int rc = child_main(input_path, dump_path);
        _exit(rc);
    }

    close(pipefd[1]);

    int status = 0;
    bool timed_out = false;
    const int poll_ms = 50;
    int elapsed_ms = 0;
    const int limit_ms = timeout_sec * 1000;

    while (true) {
        int w = waitpid(pid, &status, WNOHANG);
        if (w == pid)
            break;
        if (w == -1) {
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            break;
        }
        usleep(poll_ms * 1000);
        elapsed_ms += poll_ms;
        if (elapsed_ms >= limit_ms) {
            timed_out = true;
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            break;
        }
    }

    auto wall1 = std::chrono::high_resolution_clock::now();
    double wall_ms = std::chrono::duration<double, std::milli>(wall1 - wall0).count();

    std::string json_line;
    {
        char buf[65536];
        ssize_t n;
        std::ostringstream acc;
        while ((n = read(pipefd[0], buf, sizeof(buf) - 1)) > 0) {
            buf[n] = '\0';
            acc << buf;
        }
        json_line = acc.str();
    }
    close(pipefd[0]);

    // Best-effort remove temp dump (child may have crashed before create)
    std::error_code ec;
    if (fs::exists(dump_path)) fs::remove(dump_path, ec);

    if (timed_out) {
        std::cout << "{";
        print_json_bool("ok1", false);
        std::cout << ",";
        print_json_bool("ok2", false);
        std::cout << ",";
        print_json_size("nodes1", 0);
        std::cout << ",";
        print_json_size("nodes2", 0);
        std::cout << ",";
        print_json_bool("match_nodes", false);
        std::cout << ",";
        print_json_str("dump_path", dump_path);
        std::cout << ",";
        print_json_str("error", "timeout");
        std::cout << ",";
        print_json_num("wall_ms", wall_ms);
        std::cout << "}\n";
        return 3;
    }

    if (WIFSIGNALED(status)) {
        std::cout << "{";
        print_json_bool("ok1", false);
        std::cout << ",";
        print_json_bool("ok2", false);
        std::cout << ",";
        print_json_size("nodes1", 0);
        std::cout << ",";
        print_json_size("nodes2", 0);
        std::cout << ",";
        print_json_bool("match_nodes", false);
        std::cout << ",";
        print_json_str("dump_path", dump_path);
        std::cout << ",";
        print_json_str("error", std::string("signal ") + std::to_string(WTERMSIG(status)));
        std::cout << ",";
        print_json_num("wall_ms", wall_ms);
        std::cout << "}\n";
        return 3;
    }

    // Child printed JSON; re-print with wall_ms appended if missing
    if (!json_line.empty()) {
        // Trim to first {...}
        size_t a = json_line.find('{');
        size_t b = json_line.rfind('}');
        if (a != std::string::npos && b != std::string::npos && b > a) {
            std::string core = json_line.substr(a, b - a + 1);
            if (core.find("\"wall_ms\"") == std::string::npos) {
                if (core.size() >= 2 && core.back() == '}') {
                    core.pop_back();
                    std::ostringstream oss;
                    oss << core << ",\"wall_ms\":" << wall_ms << "}";
                    std::cout << oss.str() << "\n";
                } else {
                    std::cout << core << "\n";
                }
            } else {
                std::cout << core << "\n";
            }
        } else {
            std::cout << "{";
            print_json_bool("ok1", false);
            std::cout << ",";
            print_json_bool("ok2", false);
            std::cout << ",";
            print_json_size("nodes1", 0);
            std::cout << ",";
            print_json_size("nodes2", 0);
            std::cout << ",";
            print_json_bool("match_nodes", false);
            std::cout << ",";
            print_json_str("dump_path", "");
            std::cout << ",";
            print_json_str("error", "no_json_from_child");
            std::cout << ",";
            print_json_num("wall_ms", wall_ms);
            std::cout << "}\n";
        }
    } else {
        std::cout << "{";
        print_json_bool("ok1", false);
        std::cout << ",";
        print_json_bool("ok2", false);
        std::cout << ",";
        print_json_size("nodes1", 0);
        std::cout << ",";
        print_json_size("nodes2", 0);
        std::cout << ",";
        print_json_bool("match_nodes", false);
        std::cout << ",";
        print_json_str("dump_path", "");
        std::cout << ",";
        print_json_str("error", "empty_child_output");
        std::cout << ",";
        print_json_num("wall_ms", wall_ms);
        std::cout << "}\n";
    }

    if (WIFEXITED(status))
        return WEXITSTATUS(status) == 0 ? 0 : 2;
    return 2;
}
