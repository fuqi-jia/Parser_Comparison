// rdl_solver.cpp — Floyd-Warshall negative-cycle decision over symbolic
// strict bounds. See rdl_solver.hpp for the contract; this file mirrors
// rdl_backend.py::floyd_warshall_has_negative_cycle 1:1.

#include "rdl_solver.hpp"

#include <iostream>
#include <iterator>
#include <unordered_map>
#include <vector>

namespace rdl {

namespace {

bool floyd_warshall_has_negative_cycle(
    const std::vector<std::string>& variables,
    const std::vector<std::tuple<std::string, std::string, Bound>>& edges)
{
    const size_t n = variables.size();
    if (n == 0) return false;

    std::unordered_map<std::string, size_t> idx;
    idx.reserve(n);
    for (size_t i = 0; i < n; ++i) idx[variables[i]] = i;

    const Bound INF  = Bound::infinity();
    const Bound ZERO = Bound::zero();

    // dist[i][j] : best known bound on (variables[j] - variables[i]).
    std::vector<std::vector<Bound>> dist(n, std::vector<Bound>(n, INF));
    for (size_t i = 0; i < n; ++i) dist[i][i] = ZERO;

    for (const auto& [src, dst, w] : edges) {
        auto it_s = idx.find(src);
        auto it_d = idx.find(dst);
        if (it_s == idx.end() || it_d == idx.end()) continue;  // should not happen if variables include all endpoints
        size_t i = it_s->second, j = it_d->second;
        if (w < dist[i][j]) dist[i][j] = w;
    }

    // Standard O(n^3) all-pairs shortest paths using the symbolic Bound type.
    for (size_t k = 0; k < n; ++k) {
        auto& dk = dist[k];
        for (size_t i = 0; i < n; ++i) {
            const Bound& dik = dist[i][k];
            if (dik == INF) continue;
            auto& di = dist[i];
            for (size_t j = 0; j < n; ++j) {
                const Bound& dkj = dk[j];
                if (dkj == INF) continue;
                Bound cand = dik + dkj;
                if (cand < di[j]) di[j] = cand;
            }
        }
    }

    for (size_t i = 0; i < n; ++i) {
        if (dist[i][i] < ZERO) return true;
    }
    return false;
}

}  // namespace

std::string decide(const Payload& p) {
    if (p.status == Status::Unsupported) {
        std::cerr << "backend: unsupported input (" << (p.reason.empty() ? "no reason given" : p.reason) << ")\n";
        return "unknown";
    }
    if (p.status == Status::Error) {
        std::cerr << "backend: adapter error (" << (p.reason.empty() ? "no reason given" : p.reason) << ")\n";
        return "unknown";
    }
    if (p.status != Status::Ok) {
        std::cerr << "backend: unknown status field\n";
        return "unknown";
    }

    if (p.mode != Mode::Conjunction) {
        std::cerr << "backend: mode is not 'conjunction'; only conjunction is supported in v1\n";
        return "unknown";
    }

    // Gather variables, ensuring every constraint endpoint plus ZERO appears.
    std::vector<std::string> variables = p.variables;
    std::unordered_map<std::string, char> seen;
    for (auto& v : variables) seen[v] = 1;
    auto add_if_new = [&](const std::string& v) {
        if (!seen.count(v)) { seen[v] = 1; variables.push_back(v); }
    };
    std::vector<std::tuple<std::string, std::string, Bound>> edges;
    edges.reserve(p.constraints.size());
    for (const auto& c : p.constraints) {
        add_if_new(c.lhs);
        add_if_new(c.rhs);
        // For "lhs - rhs (op) bound", edge is rhs -> lhs with weight (bound, strict).
        edges.emplace_back(c.rhs, c.lhs, c.bound);
    }
    add_if_new("ZERO");

    if (edges.empty()) return "sat";
    return floyd_warshall_has_negative_cycle(variables, edges) ? "unsat" : "sat";
}

}  // namespace rdl
