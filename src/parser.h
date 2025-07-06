#pragma once

#include "../SMTParser/include/parser.h"

namespace SMTParser {
    // 创建Parser实例的工厂函数
    inline ParserPtr createParser() {
        return newParser();
    }

    // 从文件创建Parser实例的工厂函数
    inline ParserPtr createParserFromFile(const std::string& filename) {
        return newParser(filename);
    }

    // 获取Parser中的错误向量类型
    using ErrorVec = std::vector<std::string>;
} 