cmake_minimum_required(VERSION 3.16)
project(rdl_backend LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

# GMP — the upstream "FindGMP" module is not shipped with CMake, but the
# common Debian/Ubuntu locations are well known. We resolve manually.
find_path(GMP_INCLUDE_DIR
  NAMES gmpxx.h
  PATHS /usr/include /usr/local/include
)
find_library(GMP_LIBRARY    NAMES gmp    PATHS /usr/lib /usr/lib/x86_64-linux-gnu /usr/local/lib)
find_library(GMPXX_LIBRARY  NAMES gmpxx  PATHS /usr/lib /usr/lib/x86_64-linux-gnu /usr/local/lib)
if(NOT GMP_INCLUDE_DIR OR NOT GMP_LIBRARY OR NOT GMPXX_LIBRARY)
  message(FATAL_ERROR
    "GMP not found. Install via 'apt-get install libgmp-dev' (Debian/Ubuntu) "
    "or 'brew install gmp' (macOS). Detected: INCLUDE=${GMP_INCLUDE_DIR} "
    "LIB=${GMP_LIBRARY} LIBXX=${GMPXX_LIBRARY}")
endif()

add_library(rdl_backend_core STATIC
  src/rdl_bound.cpp
  src/rdl_payload.cpp
  src/rdl_solver.cpp
)
target_include_directories(rdl_backend_core
  PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include
  PRIVATE ${GMP_INCLUDE_DIR}
)
target_link_libraries(rdl_backend_core PUBLIC ${GMPXX_LIBRARY} ${GMP_LIBRARY})

add_executable(rdl_backend src/rdl_backend.cpp)
target_link_libraries(rdl_backend PRIVATE rdl_backend_core)

# Unit tests — runtime asserts, no framework dependency.
enable_testing()
add_executable(unit_bound tests/unit_bound.cpp)
target_link_libraries(unit_bound PRIVATE rdl_backend_core)
add_test(NAME unit_bound COMMAND unit_bound)

add_executable(unit_solver tests/unit_solver.cpp)
target_link_libraries(unit_solver PRIVATE rdl_backend_core)
add_test(NAME unit_solver COMMAND unit_solver)
