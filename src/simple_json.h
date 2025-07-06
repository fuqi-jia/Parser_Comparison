#pragma once

#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <memory>
#include <stdexcept>

// 简单的JSON解析和生成类
namespace SimpleJson {

class Value {
public:
    enum Type {
        NULL_TYPE,
        BOOL_TYPE,
        NUMBER_TYPE,
        STRING_TYPE,
        ARRAY_TYPE,
        OBJECT_TYPE
    };

    // 构造函数
    Value() : type_(NULL_TYPE) {}
    Value(bool value) : type_(BOOL_TYPE), bool_value_(value) {}
    Value(int value) : type_(NUMBER_TYPE), number_value_(value) {}
    Value(double value) : type_(NUMBER_TYPE), number_value_(value) {}
    Value(const std::string& value) : type_(STRING_TYPE), string_value_(value) {}
    Value(const char* value) : type_(STRING_TYPE), string_value_(value) {}
    
    // 数组和对象的构造函数
    Value(const std::vector<Value>& array) : type_(ARRAY_TYPE), array_value_(array) {}
    Value(const std::map<std::string, Value>& object) : type_(OBJECT_TYPE), object_value_(object) {}

    // 类型检查
    bool isNull() const { return type_ == NULL_TYPE; }
    bool isBool() const { return type_ == BOOL_TYPE; }
    bool isNumber() const { return type_ == NUMBER_TYPE; }
    bool isString() const { return type_ == STRING_TYPE; }
    bool isArray() const { return type_ == ARRAY_TYPE; }
    bool isObject() const { return type_ == OBJECT_TYPE; }

    // 获取值
    bool getBool() const { return bool_value_; }
    double getNumber() const { return number_value_; }
    const std::string& getString() const { return string_value_; }
    const std::vector<Value>& getArray() const { return array_value_; }
    const std::map<std::string, Value>& getObject() const { return object_value_; }

    // 数组和对象的操作
    Value& operator[](size_t index) {
        if (type_ != ARRAY_TYPE) {
            throw std::runtime_error("Cannot use operator[] with non-array value");
        }
        if (index >= array_value_.size()) {
            throw std::out_of_range("Array index out of range");
        }
        return array_value_[index];
    }

    Value& operator[](const std::string& key) {
        if (type_ != OBJECT_TYPE) {
            type_ = OBJECT_TYPE;
            object_value_.clear();
        }
        return object_value_[key];
    }

    // 序列化为字符串
    std::string toString() const {
        std::stringstream ss;
        serialize(ss);
        return ss.str();
    }

private:
    Type type_;
    bool bool_value_ = false;
    double number_value_ = 0;
    std::string string_value_;
    std::vector<Value> array_value_;
    std::map<std::string, Value> object_value_;

    // 序列化为输出流
    void serialize(std::ostream& out) const {
        switch (type_) {
            case NULL_TYPE:
                out << "null";
                break;
            case BOOL_TYPE:
                out << (bool_value_ ? "true" : "false");
                break;
            case NUMBER_TYPE:
                out << number_value_;
                break;
            case STRING_TYPE:
                serializeString(out, string_value_);
                break;
            case ARRAY_TYPE:
                out << "[";
                for (size_t i = 0; i < array_value_.size(); ++i) {
                    if (i > 0) out << ",";
                    array_value_[i].serialize(out);
                }
                out << "]";
                break;
            case OBJECT_TYPE:
                out << "{";
                bool first = true;
                for (const auto& item : object_value_) {
                    if (!first) out << ",";
                    first = false;
                    serializeString(out, item.first);
                    out << ":";
                    item.second.serialize(out);
                }
                out << "}";
                break;
        }
    }

    // 序列化字符串（需要转义）
    static void serializeString(std::ostream& out, const std::string& str) {
        out << "\"";
        for (char c : str) {
            switch (c) {
                case '\"': out << "\\\""; break;
                case '\\': out << "\\\\"; break;
                case '\b': out << "\\b"; break;
                case '\f': out << "\\f"; break;
                case '\n': out << "\\n"; break;
                case '\r': out << "\\r"; break;
                case '\t': out << "\\t"; break;
                default:
                    if (static_cast<unsigned char>(c) < 0x20) {
                        char buf[7];
                        sprintf(buf, "\\u%04x", c);
                        out << buf;
                    } else {
                        out << c;
                    }
            }
        }
        out << "\"";
    }
};

// 解析JSON字符串
class Parser {
public:
    static Value parse(const std::string& input) {
        Parser parser(input);
        return parser.parseValue();
    }

private:
    const std::string& input_;
    size_t pos_ = 0;

    Parser(const std::string& input) : input_(input) {}

    // 跳过空白字符
    void skipWhitespace() {
        while (pos_ < input_.length() && 
               (input_[pos_] == ' ' || input_[pos_] == '\t' || 
                input_[pos_] == '\n' || input_[pos_] == '\r')) {
            ++pos_;
        }
    }

    // 解析值
    Value parseValue() {
        skipWhitespace();
        
        if (pos_ >= input_.length()) {
            throw std::runtime_error("Unexpected end of input");
        }

        char c = input_[pos_];
        
        if (c == 'n') return parseNull();
        if (c == 't' || c == 'f') return parseBool();
        if (c == '"') return parseString();
        if (c == '[') return parseArray();
        if (c == '{') return parseObject();
        if (c == '-' || (c >= '0' && c <= '9')) return parseNumber();
        
        throw std::runtime_error(std::string("Unexpected character: ") + c);
    }

    // 解析null
    Value parseNull() {
        if (pos_ + 4 <= input_.length() && input_.substr(pos_, 4) == "null") {
            pos_ += 4;
            return Value();
        }
        throw std::runtime_error("Invalid null value");
    }

    // 解析布尔值
    Value parseBool() {
        if (pos_ + 4 <= input_.length() && input_.substr(pos_, 4) == "true") {
            pos_ += 4;
            return Value(true);
        }
        if (pos_ + 5 <= input_.length() && input_.substr(pos_, 5) == "false") {
            pos_ += 5;
            return Value(false);
        }
        throw std::runtime_error("Invalid boolean value");
    }

    // 解析字符串
    Value parseString() {
        ++pos_; // Skip opening quote
        std::string result;
        bool escaped = false;
        
        while (pos_ < input_.length()) {
            char c = input_[pos_++];
            
            if (escaped) {
                switch (c) {
                    case '"': result += '"'; break;
                    case '\\': result += '\\'; break;
                    case '/': result += '/'; break;
                    case 'b': result += '\b'; break;
                    case 'f': result += '\f'; break;
                    case 'n': result += '\n'; break;
                    case 'r': result += '\r'; break;
                    case 't': result += '\t'; break;
                    case 'u': {
                        // Unicode escape sequence
                        if (pos_ + 4 > input_.length()) {
                            throw std::runtime_error("Invalid unicode escape sequence");
                        }
                        // Simplified: just keep the escape sequence as is
                        result += "\\u" + input_.substr(pos_, 4);
                        pos_ += 4;
                        break;
                    }
                    default: result += c;
                }
                escaped = false;
            } else if (c == '\\') {
                escaped = true;
            } else if (c == '"') {
                // End of string
                return Value(result);
            } else {
                result += c;
            }
        }
        
        throw std::runtime_error("Unterminated string");
    }

    // 解析数组
    Value parseArray() {
        ++pos_; // Skip opening bracket
        std::vector<Value> result;
        
        skipWhitespace();
        if (pos_ < input_.length() && input_[pos_] == ']') {
            ++pos_;
            return Value(result);
        }
        
        while (pos_ < input_.length()) {
            result.push_back(parseValue());
            skipWhitespace();
            
            if (pos_ < input_.length() && input_[pos_] == ']') {
                ++pos_;
                return Value(result);
            }
            
            if (pos_ >= input_.length() || input_[pos_] != ',') {
                throw std::runtime_error("Expected ',' or ']' in array");
            }
            
            ++pos_; // Skip comma
            skipWhitespace();
        }
        
        throw std::runtime_error("Unterminated array");
    }

    // 解析对象
    Value parseObject() {
        ++pos_; // Skip opening brace
        std::map<std::string, Value> result;
        
        skipWhitespace();
        if (pos_ < input_.length() && input_[pos_] == '}') {
            ++pos_;
            return Value(result);
        }
        
        while (pos_ < input_.length()) {
            skipWhitespace();
            if (pos_ >= input_.length() || input_[pos_] != '"') {
                throw std::runtime_error("Expected string key in object");
            }
            
            Value key = parseString();
            skipWhitespace();
            
            if (pos_ >= input_.length() || input_[pos_] != ':') {
                throw std::runtime_error("Expected ':' after key in object");
            }
            
            ++pos_; // Skip colon
            skipWhitespace();
            
            result[key.getString()] = parseValue();
            skipWhitespace();
            
            if (pos_ < input_.length() && input_[pos_] == '}') {
                ++pos_;
                return Value(result);
            }
            
            if (pos_ >= input_.length() || input_[pos_] != ',') {
                throw std::runtime_error("Expected ',' or '}' in object");
            }
            
            ++pos_; // Skip comma
        }
        
        throw std::runtime_error("Unterminated object");
    }

    // 解析数字
    Value parseNumber() {
        size_t start_pos = pos_;
        bool is_negative = false;
        
        // Handle sign
        if (input_[pos_] == '-') {
            is_negative = true;
            ++pos_;
        }
        
        // Integer part
        while (pos_ < input_.length() && input_[pos_] >= '0' && input_[pos_] <= '9') {
            ++pos_;
        }
        
        // Fraction part
        bool has_fraction = false;
        if (pos_ < input_.length() && input_[pos_] == '.') {
            has_fraction = true;
            ++pos_;
            while (pos_ < input_.length() && input_[pos_] >= '0' && input_[pos_] <= '9') {
                ++pos_;
            }
        }
        
        // Exponent part
        bool has_exponent = false;
        if (pos_ < input_.length() && (input_[pos_] == 'e' || input_[pos_] == 'E')) {
            has_exponent = true;
            ++pos_;
            
            if (pos_ < input_.length() && (input_[pos_] == '+' || input_[pos_] == '-')) {
                ++pos_;
            }
            
            while (pos_ < input_.length() && input_[pos_] >= '0' && input_[pos_] <= '9') {
                ++pos_;
            }
        }
        
        std::string num_str = input_.substr(start_pos, pos_ - start_pos);
        
        if (has_fraction || has_exponent) {
            // Parse as double
            try {
                return Value(std::stod(num_str));
            } catch (const std::exception&) {
                throw std::runtime_error("Invalid number: " + num_str);
            }
        } else {
            // Parse as integer
            try {
                return Value(std::stoi(num_str));
            } catch (const std::exception&) {
                // If it's too large for int, try as double
                try {
                    return Value(std::stod(num_str));
                } catch (const std::exception&) {
                    throw std::runtime_error("Invalid number: " + num_str);
                }
            }
        }
    }
};

} // namespace SimpleJson 