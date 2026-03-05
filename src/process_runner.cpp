#include "process_runner.h"
#include <array>
#include <chrono>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <poll.h>
#include <sstream>
#include <unistd.h>
#include <sys/wait.h>

#ifdef __linux__
#define USE_PROC_STATUS 1
#else
#define USE_PROC_STATUS 0
#endif

namespace SMTComparison {

namespace {

constexpr size_t STDERR_SNIPPET_MAX = 512;
constexpr int POLL_MS = 50;

#if USE_PROC_STATUS
size_t readVmHWM(pid_t pid) {
    std::string path = "/proc/" + std::to_string(pid) + "/status";
    std::ifstream f(path);
    if (!f) return 0;
    std::string line;
    size_t vmhwm = 0;
    while (std::getline(f, line)) {
        if (line.compare(0, 6, "VmHWM:") == 0) {
            std::istringstream iss(line.substr(6));
            iss >> vmhwm;
            break;
        }
    }
    return vmhwm;
}
#endif

ssize_t readAvailable(int fd, std::string& out) {
    char buf[4096];
    ssize_t n = read(fd, buf, sizeof(buf));
    if (n > 0) out.append(buf, static_cast<size_t>(n));
    return n;
}

void setNonBlock(int fd) {
    int fl = fcntl(fd, F_GETFL, 0);
    if (fl >= 0) fcntl(fd, F_SETFL, fl | O_NONBLOCK);
}

} // anonymous namespace

ProcessRunResult ProcessRunner::run(const std::string& cmd, int timeout_sec) {
    ProcessRunResult res;
    res.wall_time_ms = 0;
    res.peak_rss_kb = 0;

    int stdout_pipe[2], stderr_pipe[2];
    if (pipe(stdout_pipe) != 0 || pipe(stderr_pipe) != 0) {
        res.timed_out = false;
        res.exit_code = -1;
        res.stderr_output = "pipe() failed";
        return res;
    }

    pid_t pid = fork();
    if (pid == -1) {
        close(stdout_pipe[0]); close(stdout_pipe[1]);
        close(stderr_pipe[0]); close(stderr_pipe[1]);
        res.stderr_output = "fork() failed";
        return res;
    }

    if (pid == 0) {
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        // 子进程自成进程组，这样 sh 再 fork 的 parser（如 cvc5_parser）同属该组；
        // 超时时 kill(-pid) 可杀整组，避免只杀 sh 导致 parser 悬空。
        (void)setpgid(0, 0);
        execl("/bin/sh", "sh", "-c", cmd.c_str(), (char*)nullptr);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    setNonBlock(stdout_pipe[0]);
    setNonBlock(stderr_pipe[0]);

    auto start = std::chrono::steady_clock::now();
    std::string stdout_out, stderr_out;
    size_t peak_rss = 0;
    int status = 0;
    bool child_exited = false;

    while (true) {
        struct pollfd pfd[2] = {
            { stdout_pipe[0], POLLIN, 0 },
            { stderr_pipe[0], POLLIN, 0 }
        };
        int r = poll(pfd, 2, POLL_MS);
        if (r > 0) {
            if (pfd[0].revents & POLLIN) readAvailable(stdout_pipe[0], stdout_out);
            if (pfd[1].revents & POLLIN) readAvailable(stderr_pipe[0], stderr_out);
        }

        if (waitpid(pid, &status, WNOHANG) == pid) {
            child_exited = true;
            break;
        }

#if USE_PROC_STATUS
        size_t hwm = readVmHWM(pid);
        if (hwm > peak_rss) peak_rss = hwm;
#endif

        auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        if (timeout_sec > 0 && elapsed >= timeout_sec) {
            // 杀整组（sh + 其子进程如 cvc5_parser），避免只杀 sh 留下孤儿 parser
            kill(-pid, SIGKILL);
            waitpid(pid, &status, 0);
            res.timed_out = true;
            break;
        }
    }

    if (!child_exited)
        waitpid(pid, &status, 0);

    auto end = std::chrono::steady_clock::now();
    res.wall_time_ms = std::chrono::duration<double, std::milli>(end - start).count();
    res.stdout_output = std::move(stdout_out);
    if (stderr_out.size() > STDERR_SNIPPET_MAX)
        res.stderr_output = stderr_out.substr(0, STDERR_SNIPPET_MAX) + "...";
    else
        res.stderr_output = std::move(stderr_out);
    res.peak_rss_kb = peak_rss;

    if (WIFEXITED(status)) {
        res.exit_code = WEXITSTATUS(status);
        res.term_signal = 0;
    } else if (WIFSIGNALED(status)) {
        res.exit_code = -1;
        res.term_signal = WTERMSIG(status);
    }

    close(stdout_pipe[0]);
    close(stderr_pipe[0]);
    return res;
}

} // namespace SMTComparison
