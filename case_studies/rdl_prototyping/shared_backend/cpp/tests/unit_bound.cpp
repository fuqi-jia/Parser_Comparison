// unit_bound.cpp — exercises the symbolic-strict-bound arithmetic so we
// catch regressions in (value, strict) ordering or addition. We deliberately
// avoid pulling in GoogleTest etc.: a hand-rolled CHECK macro keeps the
// case study build hermetic.

#include "rdl_bound.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

static int g_fail = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        std::fprintf(stderr, "FAIL %s:%d %s -- %s\n", __FILE__, __LINE__, #cond, msg); \
        ++g_fail; \
    } \
} while (0)

int main() {
    using rdl::Bound;

    Bound zero   = Bound::zero();
    Bound zero_s = Bound(mpq_class(0), true);     // strict zero
    Bound one    = Bound(mpq_class(1), false);
    Bound neg1   = Bound(mpq_class(-1), false);
    Bound half   = Bound(mpq_class("1/2"), false);

    // is_negative
    CHECK(neg1.is_negative(),         "(-1, false) is negative");
    CHECK(zero_s.is_negative(),       "(0, true)  is negative (strict zero)");
    CHECK(!zero.is_negative(),        "(0, false) is NOT negative");
    CHECK(!one.is_negative(),         "(1, false) is NOT negative");

    // ordering
    CHECK(zero_s < zero,              "strict zero is strictly less than (0,false)");
    CHECK(neg1 < zero_s,              "(-1,false) < strict zero");
    CHECK(zero < one,                 "(0,false) < (1,false)");
    CHECK(!(zero < zero),             "(0,false) is not < (0,false)");
    CHECK(zero == zero,               "(0,false) == (0,false)");
    CHECK(zero != zero_s,             "(0,false) != (0,true)");

    // addition
    Bound sum = neg1 + zero_s;        // (-1, true)
    CHECK(sum.value == -1 && sum.strict, "(-1,false)+(0,true) == (-1,true)");
    CHECK(sum.is_negative(),          "(-1,true) is negative");

    Bound sum2 = zero_s + zero_s;     // additive fixed point
    CHECK(sum2 == zero_s,             "(0,true)+(0,true) == (0,true) — fixed point");

    Bound sum3 = half + half;         // (1, false)
    CHECK(sum3 == one,                "(1/2,false)+(1/2,false) == (1,false)");

    // infinity sentinel
    Bound inf = Bound::infinity();
    CHECK(!(inf < zero),              "infinity not < zero");
    CHECK(zero < inf,                 "zero < infinity");

    if (g_fail) {
        std::fprintf(stderr, "unit_bound: %d failures\n", g_fail);
        return 1;
    }
    std::printf("unit_bound: all checks passed\n");
    return 0;
}
