// somt-rdl-adapter: SOMTParser-based front end for the shared RDL backend.
//
// Reads an SMT-LIB2 file with SOMTParser, walks the typed DAG, extracts
// difference-logic atoms from a top-level conjunction, and serialises them as
// rdl_atoms.json. SOMTParser is used purely as a front end -- no checkSat,
// toCNF, or model API is invoked. The shared backend at
// case_studies/rdl_prototyping/shared_backend/rdl_backend.py is then the only
// component that produces sat / unsat / unknown.

#include <gmpxx.h>
#include <somtparser/parser.h>

#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

using SOMTParser::DAGNode;
using SOMTParser::NODE_KIND;
using SOMTParser::Parser;
using NodePtr = std::shared_ptr<DAGNode>;

namespace {

struct AtomOut {
    std::string lhs;
    std::string rhs;
    std::string bound;
    bool strict = false;
    std::string source;
};

struct LinearForm {
    std::map<std::string, mpq_class> coeffs;
    mpq_class constant{0};
};

mpq_class parse_rational_literal(const std::string& raw) {
    std::string s = raw;
    auto trim = [](std::string& v) {
        size_t i = 0;
        while (i < v.size() && std::isspace(static_cast<unsigned char>(v[i]))) ++i;
        size_t j = v.size();
        while (j > i && std::isspace(static_cast<unsigned char>(v[j - 1]))) --j;
        v = v.substr(i, j - i);
    };
    trim(s);
    if (s.empty()) {
        throw std::runtime_error("empty numeric literal");
    }

    bool negative = false;
    size_t start = 0;
    if (s[0] == '+' || s[0] == '-') {
        negative = (s[0] == '-');
        start = 1;
    }
    std::string body = s.substr(start);

    if (body.find('/') != std::string::npos) {
        mpq_class r((negative ? std::string("-") : std::string("")) + body);
        r.canonicalize();
        return r;
    }

    size_t dot = body.find('.');
    if (dot == std::string::npos) {
        mpq_class r((negative ? std::string("-") : std::string("")) + body);
        r.canonicalize();
        return r;
    }

    std::string intp = body.substr(0, dot);
    std::string fracp = body.substr(dot + 1);
    if (intp.empty()) intp = "0";
    if (fracp.empty()) fracp = "0";
    std::string num = intp + fracp;
    size_t firstNonZero = num.find_first_not_of('0');
    if (firstNonZero == std::string::npos) {
        num = "0";
    } else {
        num = num.substr(firstNonZero);
    }
    std::string denom = "1";
    for (size_t i = 0; i < fracp.size(); ++i) denom.push_back('0');
    mpq_class r((negative ? std::string("-") : std::string("")) + num + "/" + denom);
    r.canonicalize();
    return r;
}

bool try_numeric(const NodePtr& n, mpq_class& out) {
    if (!n) return false;
    NODE_KIND k = n->getKind();

    if (n->isCInt() || n->isCReal()) {
        try {
            out = parse_rational_literal(n->getName());
            return true;
        } catch (...) {
            return false;
        }
    }
    if (k == NODE_KIND::NT_NEG && n->getChildrenSize() == 1) {
        mpq_class c;
        if (!try_numeric(n->getChild(0), c)) return false;
        out = -c;
        return true;
    }
    if (k == NODE_KIND::NT_SUB && n->getChildrenSize() == 1) {
        mpq_class c;
        if (!try_numeric(n->getChild(0), c)) return false;
        out = -c;
        return true;
    }
    if (k == NODE_KIND::NT_ADD) {
        mpq_class acc(0);
        for (size_t i = 0; i < n->getChildrenSize(); ++i) {
            mpq_class v;
            if (!try_numeric(n->getChild(i), v)) return false;
            acc += v;
        }
        out = acc;
        return true;
    }
    if (k == NODE_KIND::NT_MUL) {
        mpq_class acc(1);
        for (size_t i = 0; i < n->getChildrenSize(); ++i) {
            mpq_class v;
            if (!try_numeric(n->getChild(i), v)) return false;
            acc *= v;
        }
        out = acc;
        return true;
    }
    if (k == NODE_KIND::NT_DIV_REAL || k == NODE_KIND::NT_DIV_INT) {
        if (n->getChildrenSize() != 2) return false;
        mpq_class a, b;
        if (!try_numeric(n->getChild(0), a)) return false;
        if (!try_numeric(n->getChild(1), b)) return false;
        if (b == 0) return false;
        out = a / b;
        return true;
    }
    return false;
}

LinearForm scale_form(const LinearForm& a, const mpq_class& s) {
    LinearForm r;
    r.constant = a.constant * s;
    for (const auto& kv : a.coeffs) r.coeffs[kv.first] = kv.second * s;
    return r;
}

LinearForm add_form(const LinearForm& a, const LinearForm& b) {
    LinearForm r = a;
    r.constant += b.constant;
    for (const auto& kv : b.coeffs) r.coeffs[kv.first] += kv.second;
    return r;
}

bool linearize(const NodePtr& n, LinearForm& f, std::string& reason) {
    f.coeffs.clear();
    f.constant = 0;

    mpq_class numv;
    if (try_numeric(n, numv)) {
        f.constant = numv;
        return true;
    }

    if (n->isVar()) {
        if (n->isVInt() || n->isVReal()) {
            f.coeffs[n->getName()] = 1;
            f.constant = 0;
            return true;
        }
        reason = "variable of unsupported sort: " + n->getName();
        return false;
    }

    NODE_KIND k = n->getKind();

    if (k == NODE_KIND::NT_NEG && n->getChildrenSize() == 1) {
        LinearForm c;
        if (!linearize(n->getChild(0), c, reason)) return false;
        f = scale_form(c, mpq_class(-1));
        return true;
    }
    if (k == NODE_KIND::NT_ADD) {
        LinearForm acc;
        for (size_t i = 0; i < n->getChildrenSize(); ++i) {
            LinearForm c;
            if (!linearize(n->getChild(i), c, reason)) return false;
            acc = add_form(acc, c);
        }
        f = acc;
        return true;
    }
    if (k == NODE_KIND::NT_SUB) {
        if (n->getChildrenSize() == 0) {
            reason = "empty subtraction";
            return false;
        }
        LinearForm acc;
        if (!linearize(n->getChild(0), acc, reason)) return false;
        if (n->getChildrenSize() == 1) {
            f = scale_form(acc, mpq_class(-1));
            return true;
        }
        for (size_t i = 1; i < n->getChildrenSize(); ++i) {
            LinearForm c;
            if (!linearize(n->getChild(i), c, reason)) return false;
            acc = add_form(acc, scale_form(c, mpq_class(-1)));
        }
        f = acc;
        return true;
    }
    if (k == NODE_KIND::NT_MUL) {
        mpq_class scalar(1);
        bool has_var_part = false;
        LinearForm var_part;
        for (size_t i = 0; i < n->getChildrenSize(); ++i) {
            mpq_class v;
            if (try_numeric(n->getChild(i), v)) {
                scalar *= v;
                continue;
            }
            LinearForm c;
            if (!linearize(n->getChild(i), c, reason)) return false;
            if (has_var_part) {
                reason = "non-linear multiplication";
                return false;
            }
            var_part = c;
            has_var_part = true;
        }
        if (has_var_part) {
            f = scale_form(var_part, scalar);
        } else {
            f.constant = scalar;
        }
        return true;
    }
    if (k == NODE_KIND::NT_DIV_REAL || k == NODE_KIND::NT_DIV_INT) {
        if (n->getChildrenSize() != 2) {
            reason = "div with arity != 2";
            return false;
        }
        mpq_class denom;
        if (!try_numeric(n->getChild(1), denom)) {
            reason = "division by non-constant";
            return false;
        }
        if (denom == 0) {
            reason = "division by zero";
            return false;
        }
        LinearForm num;
        if (!linearize(n->getChild(0), num, reason)) return false;
        f = scale_form(num, mpq_class(1) / denom);
        return true;
    }

    reason = "unsupported arithmetic constructor";
    return false;
}

std::string mpq_to_str(const mpq_class& q) {
    std::ostringstream ss;
    ss << q;
    return ss.str();
}

bool extract_comparison(const NodePtr& n, std::vector<AtomOut>& out, std::string& reason) {
    NODE_KIND k = n->getKind();
    bool is_eq = (k == NODE_KIND::NT_EQ);
    if (!is_eq && k != NODE_KIND::NT_LE && k != NODE_KIND::NT_LT &&
        k != NODE_KIND::NT_GE && k != NODE_KIND::NT_GT) {
        reason = "non-comparison atom in P0";
        return false;
    }
    if (n->getChildrenSize() != 2) {
        reason = "comparison must be binary in P0";
        return false;
    }
    if (is_eq) {
        NodePtr c0 = n->getChild(0);
        if (!c0->isArithTerm()) {
            reason = "equality is not over an arithmetic term";
            return false;
        }
    }

    LinearForm L, R;
    if (!linearize(n->getChild(0), L, reason)) return false;
    if (!linearize(n->getChild(1), R, reason)) return false;

    LinearForm total = add_form(L, scale_form(R, mpq_class(-1)));
    mpq_class rhs_const = -total.constant;

    std::vector<std::pair<std::string, mpq_class>> nz;
    for (const auto& kv : total.coeffs) {
        if (kv.second != 0) nz.push_back(kv);
    }

    auto emit = [&](const std::string& a, const std::string& b, const mpq_class& bound, bool strict) {
        AtomOut o;
        o.lhs = a;
        o.rhs = b;
        o.bound = mpq_to_str(bound);
        o.strict = strict;
        out.push_back(o);
    };

    auto flip = [](NODE_KIND kk) {
        switch (kk) {
            case NODE_KIND::NT_LE: return NODE_KIND::NT_GE;
            case NODE_KIND::NT_LT: return NODE_KIND::NT_GT;
            case NODE_KIND::NT_GE: return NODE_KIND::NT_LE;
            case NODE_KIND::NT_GT: return NODE_KIND::NT_LT;
            default: return kk;
        }
    };

    if (nz.size() == 1) {
        const std::string& var = nz[0].first;
        mpq_class coef = nz[0].second;
        if (coef != 1 && coef != -1) {
            reason = "unary atom has non-unit coefficient";
            return false;
        }
        mpq_class b = rhs_const / coef;
        NODE_KIND op = (coef == 1) ? k : flip(k);
        if (is_eq) {
            emit(var, "ZERO", b, false);
            emit("ZERO", var, -b, false);
        } else if (op == NODE_KIND::NT_LE) {
            emit(var, "ZERO", b, false);
        } else if (op == NODE_KIND::NT_LT) {
            emit(var, "ZERO", b, true);
        } else if (op == NODE_KIND::NT_GE) {
            emit("ZERO", var, -b, false);
        } else if (op == NODE_KIND::NT_GT) {
            emit("ZERO", var, -b, true);
        }
        return true;
    }

    if (nz.size() == 2) {
        std::string a = nz[0].first;
        std::string b = nz[1].first;
        mpq_class ca = nz[0].second;
        mpq_class cb = nz[1].second;
        if (!((ca == 1 && cb == -1) || (ca == -1 && cb == 1))) {
            reason = "RDL requires (+1,-1) coefficients; got non-unit pair";
            return false;
        }
        std::string pos = (ca == 1) ? a : b;
        std::string neg = (ca == 1) ? b : a;
        if (is_eq) {
            emit(pos, neg, rhs_const, false);
            emit(neg, pos, -rhs_const, false);
        } else if (k == NODE_KIND::NT_LE) {
            emit(pos, neg, rhs_const, false);
        } else if (k == NODE_KIND::NT_LT) {
            emit(pos, neg, rhs_const, true);
        } else if (k == NODE_KIND::NT_GE) {
            emit(neg, pos, -rhs_const, false);
        } else if (k == NODE_KIND::NT_GT) {
            emit(neg, pos, -rhs_const, true);
        }
        return true;
    }

    reason = "atom is not a difference constraint (variable count = " + std::to_string(nz.size()) + ")";
    return false;
}

bool walk_assertion(const NodePtr& a, std::vector<AtomOut>& out, std::string& reason) {
    if (!a) {
        reason = "null assertion";
        return false;
    }
    NODE_KIND k = a->getKind();
    if (a->isTrue()) return true;
    if (a->isFalse()) {
        // Encode as a self-loop with strictly-negative weight: ZERO - ZERO < 0.
        AtomOut o;
        o.lhs = "ZERO";
        o.rhs = "ZERO";
        o.bound = "0";
        o.strict = true;
        o.source = "false";
        out.push_back(o);
        return true;
    }
    if (k == NODE_KIND::NT_AND) {
        for (size_t i = 0; i < a->getChildrenSize(); ++i) {
            if (!walk_assertion(a->getChild(i), out, reason)) return false;
        }
        return true;
    }
    if (a->isOr() || a->isNot() || a->isImplies() || a->isXor() || a->isIte()) {
        reason = "non-conjunctive Boolean structure";
        return false;
    }
    if (a->getKind() == NODE_KIND::NT_FORALL || a->getKind() == NODE_KIND::NT_EXISTS) {
        reason = "quantifier in P0";
        return false;
    }
    if (k == NODE_KIND::NT_LE || k == NODE_KIND::NT_LT ||
        k == NODE_KIND::NT_GE || k == NODE_KIND::NT_GT ||
        k == NODE_KIND::NT_EQ) {
        return extract_comparison(a, out, reason);
    }
    reason = "unsupported expression at top level";
    return false;
}

std::string json_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 2);
    for (char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", static_cast<unsigned>(c));
                    out += buf;
                } else {
                    out += c;
                }
        }
    }
    return out;
}

void write_unsupported(std::ostream& os, const std::string& reason) {
    os << "{\n";
    os << "  \"status\": \"unsupported\",\n";
    os << "  \"frontend\": \"somtparser\",\n";
    os << "  \"reason\": \"" << json_escape(reason) << "\"\n";
    os << "}\n";
}

void write_error(std::ostream& os, const std::string& reason, const std::string& detail) {
    os << "{\n";
    os << "  \"status\": \"error\",\n";
    os << "  \"frontend\": \"somtparser\",\n";
    os << "  \"reason\": \"" << json_escape(reason) << "\",\n";
    os << "  \"detail\": \"" << json_escape(detail) << "\"\n";
    os << "}\n";
}

void write_ok(std::ostream& os,
              const std::vector<std::string>& variables,
              const std::vector<AtomOut>& atoms) {
    os << "{\n";
    os << "  \"status\": \"ok\",\n";
    os << "  \"frontend\": \"somtparser\",\n";
    os << "  \"mode\": \"conjunction\",\n";
    os << "  \"variables\": [";
    for (size_t i = 0; i < variables.size(); ++i) {
        if (i > 0) os << ", ";
        os << "\"" << json_escape(variables[i]) << "\"";
    }
    os << "],\n";
    os << "  \"constraints\": [";
    for (size_t i = 0; i < atoms.size(); ++i) {
        const AtomOut& a = atoms[i];
        os << (i == 0 ? "\n    " : ",\n    ");
        os << "{\"lhs\": \"" << json_escape(a.lhs)
           << "\", \"rhs\": \"" << json_escape(a.rhs)
           << "\", \"bound\": \"" << json_escape(a.bound)
           << "\", \"strict\": " << (a.strict ? "true" : "false");
        if (!a.source.empty()) {
            os << ", \"source\": \"" << json_escape(a.source) << "\"";
        }
        os << "}";
    }
    if (!atoms.empty()) os << "\n  ";
    os << "]\n";
    os << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: somt-rdl-adapter input.smt2 output.json" << std::endl;
        return 2;
    }
    const std::string in_path = argv[1];
    const std::string out_path = argv[2];

    Parser parser;
    bool parsed = false;
    std::string parse_err;
    try {
        parsed = parser.parse(in_path);
    } catch (const std::exception& e) {
        parse_err = e.what();
        parsed = false;
    } catch (...) {
        parse_err = "unknown exception";
        parsed = false;
    }

    if (!parsed) {
        std::ofstream os(out_path);
        if (!os) {
            std::cerr << "somt-rdl-adapter: cannot open " << out_path << std::endl;
            return 1;
        }
        write_error(os, "parse failed", parse_err.empty() ? "SOMTParser::Parser::parse returned false" : parse_err);
        return 0;
    }

    std::vector<AtomOut> atoms;
    std::string reason;
    bool unsupported = false;
    try {
        std::vector<NodePtr> assertions = parser.getAssertions();
        for (const NodePtr& a : assertions) {
            if (!walk_assertion(a, atoms, reason)) {
                unsupported = true;
                break;
            }
        }
    } catch (const std::exception& e) {
        std::ofstream os(out_path);
        write_error(os, "exception during traversal", e.what());
        return 0;
    }

    std::ofstream os(out_path);
    if (!os) {
        std::cerr << "somt-rdl-adapter: cannot open " << out_path << std::endl;
        return 1;
    }

    if (unsupported) {
        write_unsupported(os, reason);
        return 0;
    }

    std::vector<std::string> variables;
    try {
        for (const NodePtr& v : parser.getDeclaredVariables()) {
            if (v && (v->isVInt() || v->isVReal())) {
                variables.push_back(v->getName());
            }
        }
    } catch (...) {
        // best effort: variables list will be filled in by the backend from constraints
    }
    bool needs_zero = false;
    for (const AtomOut& a : atoms) {
        if (a.lhs == "ZERO" || a.rhs == "ZERO") { needs_zero = true; break; }
    }
    if (needs_zero) variables.push_back("ZERO");

    write_ok(os, variables, atoms);
    return 0;
}
