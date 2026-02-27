#pragma once

#include <string>
#include <set>

namespace SMTComparison {

// 文件级 feature：脚本中出现的 commands 与 theory/features（替代“语法覆盖率”）
struct FileFeatures {
    std::set<std::string> commands;   // set-logic, declare-fun, assert, check-sat, get-model, ...
    std::set<std::string> theories;   // BV, FP, LIA, LRA, ...
    std::set<std::string> features;   // Quantifiers, Let, Datatypes, ...
};

class FeatureExtractor {
public:
    static FileFeatures extractFromFile(const std::string& path);
};

} // namespace SMTComparison
