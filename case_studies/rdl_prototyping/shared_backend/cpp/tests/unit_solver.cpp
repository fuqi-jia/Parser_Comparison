// unit_solver.cpp — Floyd-Warshall regression suite over hand-written
// payloads. Covers conjunction-only SAT/UNSAT cases plus the cycle
// edge-cases that broke the original Bellman-Ford prototype (see the
// docstring at the top of rdl_backend.py).

#include "rdl_payload.hpp"
#include "rdl_solver.hpp"

#include <cstdio>
#include <string>

static int g_fail = 0;

#define EXPECT_EQ(actual, expected, msg) do { \
    std::string a = (actual); \
    if (a != (expected)) { \
        std::fprintf(stderr, "FAIL %s:%d %s -- got '%s', expected '%s'\n", \
                     __FILE__, __LINE__, msg, a.c_str(), (expected)); \
        ++g_fail; \
    } \
} while (0)

namespace {

rdl::Payload make_ok(std::vector<std::string> vars,
                     std::vector<std::tuple<std::string, std::string,
                                            std::string, bool>> constraints) {
    rdl::Payload p;
    p.status = rdl::Status::Ok;
    p.mode   = rdl::Mode::Conjunction;
    p.frontend = "test";
    p.variables = std::move(vars);
    for (const auto& [lhs, rhs, bound, strict] : constraints) {
        rdl::Constraint c;
        c.lhs    = lhs;
        c.rhs    = rhs;
        c.bound  = rdl::Bound(rdl::parse_bound_string(bound), strict);
        p.constraints.push_back(std::move(c));
    }
    return p;
}

}  // namespace

int main() {
    // 1. Empty: trivially sat.
    {
        rdl::Payload p = make_ok({"x"}, {});
        EXPECT_EQ(rdl::decide(p), "sat", "empty conjunction is sat");
    }

    // 2. Two single constraints, satisfiable: x - y <= 3, y - x <= 5
    //    cycle weight = 8 >= 0 ⇒ sat
    {
        rdl::Payload p = make_ok({"x", "y"}, {
            {"x", "y", "3", false},
            {"y", "x", "5", false},
        });
        EXPECT_EQ(rdl::decide(p), "sat", "x-y<=3 ∧ y-x<=5 is sat");
    }

    // 3. Trivially unsat negative cycle: x - y <= -1, y - x <= 0
    //    cycle weight = -1 ⇒ unsat
    {
        rdl::Payload p = make_ok({"x", "y"}, {
            {"x", "y", "-1", false},
            {"y", "x", "0",  false},
        });
        EXPECT_EQ(rdl::decide(p), "unsat", "x-y<=-1 ∧ y-x<=0 is unsat");
    }

    // 4. Strict-zero cycle: x - y <= 0 strict, y - x <= 0 ⇒ unsat.
    //    This is the Bellman-Ford-defeating case; Floyd-Warshall handles it.
    {
        rdl::Payload p = make_ok({"x", "y"}, {
            {"x", "y", "0", true},
            {"y", "x", "0", false},
        });
        EXPECT_EQ(rdl::decide(p), "unsat", "x-y<0 ∧ y-x<=0 is unsat (strict-zero cycle)");
    }

    // 5. Rational bound: (x - y <= 1/2) ∧ (y - x <= -3/4) ⇒ -1/4 < 0 ⇒ unsat.
    {
        rdl::Payload p = make_ok({"x", "y"}, {
            {"x", "y", "1/2",  false},
            {"y", "x", "-3/4", false},
        });
        EXPECT_EQ(rdl::decide(p), "unsat", "rational unsat cycle");
    }

    // 6. ZERO-anchored unary bound: x <= -1 modelled as (x - ZERO <= -1),
    //    plus ZERO <= x as (ZERO - x <= 0). cycle = -1 ⇒ unsat.
    {
        rdl::Payload p = make_ok({"x", "ZERO"}, {
            {"x",    "ZERO", "-1", false},
            {"ZERO", "x",    "0",  false},
        });
        EXPECT_EQ(rdl::decide(p), "unsat", "ZERO-anchored unsat");
    }

    // 7. Bigger sat case: chain of 5 vars.
    {
        rdl::Payload p = make_ok({"x1","x2","x3","x4","x5"}, {
            {"x2","x1","1",false}, {"x3","x2","1",false}, {"x4","x3","1",false},
            {"x5","x4","1",false}, {"x1","x5","-100",false}, // x1-x5<=-100, y total = x2-x1+x3-x2+...+x1-x5 = -96 (not a cycle on these atoms) -- still sat
        });
        // cycle ZERO doesn't include — only the closed path x1→x2→x3→x4→x5→x1 with weights 1+1+1+1+(-100)? careful:
        // edges from constraints: x2-x1<=1 ⇒ x1→x2 weight 1; x3-x2<=1 ⇒ x2→x3 weight 1; ... x5-x4<=1 ⇒ x4→x5 weight 1; x1-x5<=-100 ⇒ x5→x1 weight -100.
        // cycle x1→x2→x3→x4→x5→x1 sums to 1+1+1+1+(-100) = -96 < 0 ⇒ UNSAT.
        EXPECT_EQ(rdl::decide(p), "unsat", "5-chain with x1-x5<=-100");
    }

    // 8. Status != Ok ⇒ unknown.
    {
        rdl::Payload p;
        p.status = rdl::Status::Unsupported;
        p.reason = "demo";
        EXPECT_EQ(rdl::decide(p), "unknown", "unsupported status yields unknown");
    }

    if (g_fail) {
        std::fprintf(stderr, "unit_solver: %d failures\n", g_fail);
        return 1;
    }
    std::printf("unit_solver: all checks passed\n");
    return 0;
}
