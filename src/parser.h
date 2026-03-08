#pragma once

#include "somtparser/parser.h"  // SOMTParser/include/somtparser/parser.h

namespace SMTParser {
    // 兼容旧名：封装 SOMTParser 库
    inline SOMTParser::ParserPtr createParser() {
        return SOMTParser::newParser();
    }
    inline SOMTParser::ParserPtr createParserFromFile(const std::string& filename) {
        return SOMTParser::newParser(filename);
    }
    using ErrorVec = std::vector<std::string>;
} 