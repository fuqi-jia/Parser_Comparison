// rdl_payload.cpp — load `rdl_atoms.json` into Payload.
//
// We deliberately roll a minimal JSON parser instead of pulling in a
// third-party dependency:
//
//   * the schema we accept is extremely small (objects, arrays, strings,
//     booleans, numbers, null) and rigid;
//   * keeping the backend dependency-free (only GMP) eases reviewer audit
//     of the "shared backend" fairness contract;
//   * the parser is ~200 lines and exercised by 100 synthetic instances
//     plus all real benchmarks.

#include "rdl_payload.hpp"

#include <fstream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <variant>

namespace rdl {

namespace {

// ---------- A tiny JSON tree ----------

struct JsonValue;
using JsonObject = std::map<std::string, JsonValue>;
using JsonArray  = std::vector<JsonValue>;

struct JsonValue {
    enum class T { Null, Bool, Number, String, Array, Object } type = T::Null;
    bool         b = false;
    std::string  s;          // for String AND for Number (raw token)
    std::shared_ptr<JsonArray>  arr;
    std::shared_ptr<JsonObject> obj;

    static JsonValue make_null()                  { JsonValue v; v.type = T::Null;   return v; }
    static JsonValue make_bool(bool x)            { JsonValue v; v.type = T::Bool;   v.b = x; return v; }
    static JsonValue make_number(std::string raw) { JsonValue v; v.type = T::Number; v.s = std::move(raw); return v; }
    static JsonValue make_string(std::string x)   { JsonValue v; v.type = T::String; v.s = std::move(x); return v; }
    static JsonValue make_array()                 { JsonValue v; v.type = T::Array;  v.arr = std::make_shared<JsonArray>(); return v; }
    static JsonValue make_object()                { JsonValue v; v.type = T::Object; v.obj = std::make_shared<JsonObject>(); return v; }
};

// ---------- Parser ----------

class JsonParser {
public:
    explicit JsonParser(const std::string& s) : s_(s) {}

    JsonValue parse_top() {
        skip_ws();
        JsonValue v = parse_value();
        skip_ws();
        if (i_ < s_.size()) fail("trailing garbage after value");
        return v;
    }

private:
    const std::string& s_;
    size_t             i_ = 0;

    [[noreturn]] void fail(const std::string& msg) {
        // Show line/col for easier debugging.
        size_t line = 1, col = 1;
        for (size_t k = 0; k < i_ && k < s_.size(); ++k) {
            if (s_[k] == '\n') { ++line; col = 1; } else { ++col; }
        }
        std::ostringstream oss;
        oss << "json parse error at line " << line << " col " << col << ": " << msg;
        throw std::runtime_error(oss.str());
    }

    void skip_ws() {
        while (i_ < s_.size()) {
            char c = s_[i_];
            if (c == ' ' || c == '\t' || c == '\r' || c == '\n') ++i_;
            else break;
        }
    }

    char peek() { if (i_ >= s_.size()) fail("unexpected end of input"); return s_[i_]; }

    JsonValue parse_value() {
        skip_ws();
        if (i_ >= s_.size()) fail("unexpected end of input");
        char c = s_[i_];
        if (c == '{') return parse_object();
        if (c == '[') return parse_array();
        if (c == '"') return JsonValue::make_string(parse_string());
        if (c == 't' || c == 'f') return parse_bool();
        if (c == 'n') return parse_null();
        return parse_number();
    }

    JsonValue parse_object() {
        ++i_;  // consume '{'
        JsonValue out = JsonValue::make_object();
        skip_ws();
        if (i_ < s_.size() && s_[i_] == '}') { ++i_; return out; }
        while (true) {
            skip_ws();
            if (i_ >= s_.size() || s_[i_] != '"') fail("expected string key in object");
            std::string key = parse_string();
            skip_ws();
            if (i_ >= s_.size() || s_[i_] != ':') fail("expected ':' after object key");
            ++i_;
            JsonValue val = parse_value();
            out.obj->emplace(std::move(key), std::move(val));
            skip_ws();
            if (i_ < s_.size() && s_[i_] == ',') { ++i_; continue; }
            if (i_ < s_.size() && s_[i_] == '}') { ++i_; return out; }
            fail("expected ',' or '}' inside object");
        }
    }

    JsonValue parse_array() {
        ++i_;  // consume '['
        JsonValue out = JsonValue::make_array();
        skip_ws();
        if (i_ < s_.size() && s_[i_] == ']') { ++i_; return out; }
        while (true) {
            JsonValue v = parse_value();
            out.arr->push_back(std::move(v));
            skip_ws();
            if (i_ < s_.size() && s_[i_] == ',') { ++i_; continue; }
            if (i_ < s_.size() && s_[i_] == ']') { ++i_; return out; }
            fail("expected ',' or ']' inside array");
        }
    }

    std::string parse_string() {
        if (s_[i_] != '"') fail("expected '\"'");
        ++i_;
        std::string out;
        while (i_ < s_.size()) {
            char c = s_[i_++];
            if (c == '"') return out;
            if (c == '\\') {
                if (i_ >= s_.size()) fail("unterminated escape");
                char e = s_[i_++];
                switch (e) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    case 'u': {
                        // We don't expect non-ASCII in payloads, but accept and
                        // emit raw bytes for the BMP code point.
                        if (i_ + 4 > s_.size()) fail("bad \\u escape");
                        unsigned cp = 0;
                        for (int k = 0; k < 4; ++k) {
                            char h = s_[i_++];
                            cp <<= 4;
                            if (h >= '0' && h <= '9') cp |= unsigned(h - '0');
                            else if (h >= 'a' && h <= 'f') cp |= unsigned(h - 'a' + 10);
                            else if (h >= 'A' && h <= 'F') cp |= unsigned(h - 'A' + 10);
                            else fail("bad hex digit in \\u escape");
                        }
                        if (cp < 0x80) out.push_back(char(cp));
                        else if (cp < 0x800) {
                            out.push_back(char(0xC0 | (cp >> 6)));
                            out.push_back(char(0x80 | (cp & 0x3F)));
                        } else {
                            out.push_back(char(0xE0 | (cp >> 12)));
                            out.push_back(char(0x80 | ((cp >> 6) & 0x3F)));
                            out.push_back(char(0x80 | (cp & 0x3F)));
                        }
                        break;
                    }
                    default: fail("unknown escape");
                }
            } else {
                out.push_back(c);
            }
        }
        fail("unterminated string");
    }

    JsonValue parse_bool() {
        if (s_.compare(i_, 4, "true") == 0)  { i_ += 4; return JsonValue::make_bool(true); }
        if (s_.compare(i_, 5, "false") == 0) { i_ += 5; return JsonValue::make_bool(false); }
        fail("expected true|false");
    }

    JsonValue parse_null() {
        if (s_.compare(i_, 4, "null") == 0) { i_ += 4; return JsonValue::make_null(); }
        fail("expected null");
    }

    JsonValue parse_number() {
        size_t start = i_;
        if (i_ < s_.size() && (s_[i_] == '-' || s_[i_] == '+')) ++i_;
        while (i_ < s_.size()) {
            char c = s_[i_];
            if ((c >= '0' && c <= '9') || c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-') ++i_;
            else break;
        }
        if (start == i_) fail("expected number");
        return JsonValue::make_number(s_.substr(start, i_ - start));
    }
};

// ---------- Field extraction helpers ----------

const JsonValue* get_field(const JsonValue& obj, const std::string& key) {
    if (obj.type != JsonValue::T::Object || !obj.obj) return nullptr;
    auto it = obj.obj->find(key);
    if (it == obj.obj->end()) return nullptr;
    return &it->second;
}

std::string require_string(const JsonValue& v, const std::string& path) {
    if (v.type != JsonValue::T::String) throw std::runtime_error(path + ": expected string");
    return v.s;
}

bool require_bool(const JsonValue& v, const std::string& path) {
    if (v.type != JsonValue::T::Bool) throw std::runtime_error(path + ": expected bool");
    return v.b;
}

}  // namespace (anonymous)

mpq_class parse_bound_string(const std::string& text) {
    std::string s = text;
    // strip whitespace
    while (!s.empty() && (s.front() == ' ' || s.front() == '\t')) s.erase(s.begin());
    while (!s.empty() && (s.back()  == ' ' || s.back()  == '\t')) s.pop_back();
    if (s.empty()) throw std::runtime_error("empty numeric literal");

    // Decimal-with-dot: convert "3.5" / "-0.25" into "35/10" / "-25/100" so
    // mpq_class can parse it exactly. mpq_class itself does NOT accept
    // decimal fractions.
    auto dot = s.find('.');
    if (dot != std::string::npos) {
        bool neg = false;
        std::string digits = s;
        if (digits[0] == '-') { neg = true; digits.erase(digits.begin()); dot -= 1; }
        else if (digits[0] == '+') { digits.erase(digits.begin()); dot -= 1; }
        std::string intp = digits.substr(0, dot);
        std::string frac = digits.substr(dot + 1);
        if (intp.empty()) intp = "0";
        for (char c : frac) {
            if (c < '0' || c > '9') throw std::runtime_error("bad decimal literal: " + text);
        }
        for (char c : intp) {
            if (c < '0' || c > '9') throw std::runtime_error("bad decimal literal: " + text);
        }
        std::string denom = "1";
        denom.append(frac.size(), '0');
        std::string num = intp + frac;
        // Strip leading zeros from num (but keep at least one digit).
        size_t lead = num.find_first_not_of('0');
        if (lead == std::string::npos) num = "0";
        else if (lead > 0) num = num.substr(lead);
        std::string repr = (neg ? "-" : "") + num + "/" + denom;
        try {
            mpq_class q(repr);
            q.canonicalize();
            return q;
        } catch (std::exception&) {
            throw std::runtime_error("bad decimal literal: " + text);
        }
    }

    try {
        mpq_class q(s);
        q.canonicalize();
        return q;
    } catch (std::exception&) {
        throw std::runtime_error("bad numeric literal: " + text);
    }
}

Payload load_payload(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("cannot open " + path);
    std::ostringstream buf;
    buf << f.rdbuf();
    std::string text = buf.str();

    JsonParser parser(text);
    JsonValue top = parser.parse_top();
    if (top.type != JsonValue::T::Object)
        throw std::runtime_error("$: top-level value must be a JSON object");

    Payload out;

    if (const JsonValue* v = get_field(top, "status")) {
        std::string s = require_string(*v, "$.status");
        if (s == "ok") out.status = Status::Ok;
        else if (s == "unsupported") out.status = Status::Unsupported;
        else if (s == "error") out.status = Status::Error;
        else out.status = Status::Other;
    }

    if (const JsonValue* v = get_field(top, "frontend"))
        out.frontend = require_string(*v, "$.frontend");

    if (const JsonValue* v = get_field(top, "reason"))
        out.reason = require_string(*v, "$.reason");

    if (const JsonValue* v = get_field(top, "mode")) {
        std::string m = require_string(*v, "$.mode");
        if (m == "conjunction") out.mode = Mode::Conjunction;
        else if (m == "boolean") out.mode = Mode::Boolean;
        else out.mode = Mode::Other;
    } else {
        // default matches rdl_backend.py: assume conjunction if status==ok
        out.mode = Mode::Conjunction;
    }

    if (out.status != Status::Ok) return out;
    if (out.mode != Mode::Conjunction) return out;

    if (const JsonValue* v = get_field(top, "variables")) {
        if (v->type != JsonValue::T::Array) throw std::runtime_error("$.variables: expected array");
        for (size_t i = 0; i < v->arr->size(); ++i) {
            const JsonValue& item = (*v->arr)[i];
            out.variables.push_back(require_string(item, "$.variables[" + std::to_string(i) + "]"));
        }
    }

    if (const JsonValue* v = get_field(top, "constraints")) {
        if (v->type != JsonValue::T::Array) throw std::runtime_error("$.constraints: expected array");
        for (size_t i = 0; i < v->arr->size(); ++i) {
            const JsonValue& c = (*v->arr)[i];
            std::string prefix = "$.constraints[" + std::to_string(i) + "]";
            if (c.type != JsonValue::T::Object) throw std::runtime_error(prefix + ": expected object");
            Constraint cc;
            const JsonValue* lhs = get_field(c, "lhs");
            const JsonValue* rhs = get_field(c, "rhs");
            const JsonValue* bnd = get_field(c, "bound");
            const JsonValue* str = get_field(c, "strict");
            if (!lhs || !rhs || !bnd || !str)
                throw std::runtime_error(prefix + ": missing one of lhs/rhs/bound/strict");
            cc.lhs    = require_string(*lhs, prefix + ".lhs");
            cc.rhs    = require_string(*rhs, prefix + ".rhs");
            cc.bound  = Bound(parse_bound_string(require_string(*bnd, prefix + ".bound")),
                              require_bool(*str, prefix + ".strict"));
            if (const JsonValue* src = get_field(c, "source"))
                cc.source = require_string(*src, prefix + ".source");
            out.constraints.push_back(std::move(cc));
        }
    }

    return out;
}

}  // namespace rdl
