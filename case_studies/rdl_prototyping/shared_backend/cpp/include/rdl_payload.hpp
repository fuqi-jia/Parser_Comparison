// rdl_payload.hpp — in-memory representation of an `rdl_atoms.json` payload.
//
// The JSON schema is the same one documented at
//   case_studies/rdl_prototyping/schema/rdl_atoms.schema.json
// and consumed by the Python reference backend. We accept exactly the
// fragment that the conjunction-only P0 backend cares about: status,
// frontend, mode, variables, constraints; "reason" for diagnostics. The
// "boolean" mode is parsed shallowly so the backend can emit "unknown"
// without crashing.

#pragma once

#include "rdl_bound.hpp"

#include <string>
#include <vector>

namespace rdl {

enum class Status {
    Ok,
    Unsupported,
    Error,
    Other          // unknown / missing
};

enum class Mode {
    Conjunction,
    Boolean,
    Other
};

struct Constraint {
    std::string lhs;
    std::string rhs;
    Bound       bound;     // (value, strict) — value parsed from JSON "bound", strict from JSON "strict"
    std::string source;    // verbatim SMT-LIB text for debugging only
};

struct Payload {
    Status                    status   = Status::Other;
    Mode                      mode     = Mode::Other;
    std::string               frontend;
    std::string               reason;
    std::vector<std::string>  variables;
    std::vector<Constraint>   constraints;
};

// Reads the file at `path` and parses it into a Payload. Throws
// std::runtime_error on any IO error, malformed JSON, or schema violation
// (e.g. constraint with non-string bound). The harness translates such an
// error into a "backend: payload error: ..." stderr message + verdict
// "unknown", mirroring rdl_backend.py main().
Payload load_payload(const std::string& path);

// Parse a numeric literal as written by adapters: decimal int, signed int,
// decimal fraction (e.g. "3.5"), or rational (e.g. "7/2"). Throws
// std::runtime_error on anything mpq_class refuses.
mpq_class parse_bound_string(const std::string& text);

}  // namespace rdl
