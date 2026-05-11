// rdl_solver.hpp — Floyd-Warshall negative-cycle decision for QF_RDL.
//
// `decide(payload)` returns "sat" / "unsat" / "unknown" using the same
// algorithm as the Python reference (rdl_backend.py::decide):
//
//   1. If status != ok, log a reason on stderr and return "unknown".
//   2. If mode != "conjunction", log and return "unknown" (boolean mode is
//      out of scope for the P0 backend).
//   3. Build the difference-constraint graph: for each
//      "lhs - rhs (op) bound" constraint, add a directed edge
//      rhs -> lhs with symbolic weight Bound(bound, strict).
//   4. Run all-pairs Floyd-Warshall over symbolic bounds. The formula is
//      unsat iff some dist[i][i] is strictly less than (0, false) — i.e.
//      Bound::is_negative() is true for some cycle. Otherwise sat.

#pragma once

#include "rdl_payload.hpp"
#include <string>

namespace rdl {

std::string decide(const Payload& p);

}  // namespace rdl
