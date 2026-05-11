// rdl_backend.cpp — entry point. CLI:
//
//   rdl_backend rdl_atoms.json
//
// Prints exactly one of "sat" / "unsat" / "unknown" on stdout. On bad
// input it logs a diagnostic on stderr, prints "unknown", and returns 1.
// Successful decision returns 0. Matches the Python reference
// (shared_backend/rdl_backend.py::main).

#include "rdl_payload.hpp"
#include "rdl_solver.hpp"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: rdl_backend rdl_atoms.json\n";
        std::cout << "unknown\n";
        return 1;
    }
    const std::string path = argv[1];

    rdl::Payload payload;
    try {
        payload = rdl::load_payload(path);
    } catch (const std::exception& e) {
        std::cerr << "backend: " << e.what() << "\n";
        std::cout << "unknown\n";
        return 1;
    }

    std::string verdict;
    try {
        verdict = rdl::decide(payload);
    } catch (const std::exception& e) {
        std::cerr << "backend: payload error: " << e.what() << "\n";
        std::cout << "unknown\n";
        return 1;
    }
    std::cout << verdict << "\n";
    return 0;
}
