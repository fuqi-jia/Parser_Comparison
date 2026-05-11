// rdl_bound.hpp — symbolic strict bound (value, strict) over rationals.
//
// Mirrors shared_backend/rdl_backend.py::Bound 1:1. A "bound" is the pair
// (value, strict) such that the lex order
//   (a, s_a) < (b, s_b)  iff  a < b  or  (a == b and s_a and not s_b)
// captures "<= bound" vs "<  bound" uniformly. Addition is
//   (a, s_a) + (b, s_b) == (a + b, s_a or s_b)
// so that path concatenation in the constraint graph adds bounds and any
// strict edge along the path makes the resulting bound strict.
//
// is_negative() is the negative-cycle predicate: value < 0 OR (value == 0
// and strict). This is the SAME criterion the Python reference uses
// (rdl_backend.py:60-66).

#pragma once

#include <gmpxx.h>
#include <utility>

namespace rdl {

class Bound {
public:
    mpq_class value;
    bool strict;

    Bound() : value(0), strict(false) {}
    Bound(mpq_class v, bool s) : value(std::move(v)), strict(s) {}

    Bound operator+(const Bound& o) const {
        return Bound(value + o.value, strict || o.strict);
    }

    bool operator==(const Bound& o) const {
        return value == o.value && strict == o.strict;
    }

    bool operator!=(const Bound& o) const { return !(*this == o); }

    bool operator<(const Bound& o) const {
        if (value != o.value) return value < o.value;
        return strict && !o.strict;
    }

    bool operator<=(const Bound& o) const { return *this == o || *this < o; }
    bool operator>(const Bound& o)  const { return o < *this; }
    bool operator>=(const Bound& o) const { return o <= *this; }

    bool is_negative() const {
        if (value < 0) return true;
        return value == 0 && strict;
    }

    static Bound zero() { return Bound(mpq_class(0), false); }
    static Bound infinity();
};

}  // namespace rdl
