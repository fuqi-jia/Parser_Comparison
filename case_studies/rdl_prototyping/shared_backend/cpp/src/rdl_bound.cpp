#include "rdl_bound.hpp"

namespace rdl {

Bound Bound::infinity() {
    // 10^30 — matches the Python reference (rdl_backend.py:73).
    mpq_class v("1000000000000000000000000000000");
    return Bound(v, false);
}

}  // namespace rdl
