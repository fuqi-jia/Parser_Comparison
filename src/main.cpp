
#include "parser.h"

using namespace SMTLIBParser;

int main(int argc, char* argv[]) {
    
    // the input parser
    std::shared_ptr<SMTLIBParser::Parser> parser = 
        std::make_shared<SMTLIBParser::Parser>();

    // the input file
    std::string input_file = argv[1];

    // parse the input file
    if(parser->parse(input_file)) {
        std::cout << "parse success" << std::endl;
    } else {
        std::cout << "parse failed" << std::endl;
    }

    return 0;
}