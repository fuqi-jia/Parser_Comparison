cmake_minimum_required(VERSION 3.10)

project(SMT_Parser_Comparison VERSION 1.0)

# set c++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# compile options
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -O3 -Wall -Wextra -Werror")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-unused-but-set-variable -Wno-unused-value")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-unused-local-typedefs")

# set SMTParser build options
set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build shared libraries" FORCE)

# Conda：不改 SMTParser 时，让子目录里 pkg_check_modules(MPFR/gmp) 找到 conda 的 gmp/mpfr
if(DEFINED ENV{CONDA_PREFIX} AND NOT "$ENV{CONDA_PREFIX}" STREQUAL "")
  set(ENV{PKG_CONFIG_PATH} "$ENV{CONDA_PREFIX}/lib/pkgconfig:$ENV{CONDA_PREFIX}/share/pkgconfig:$ENV{PKG_CONFIG_PATH}")
  message(STATUS "PKG_CONFIG_PATH 已加入 CONDA_PREFIX，SMTParser 将使用 conda 的 gmp/mpfr")
endif()

# add SMTParser subdirectory
add_subdirectory(SMTParser)

# find GMP library
find_package(PkgConfig REQUIRED)
pkg_check_modules(GMP REQUIRED gmp)
pkg_check_modules(GMPXX REQUIRED gmpxx)

# add src subdirectory
add_subdirectory(src)

# get all source files
file(GLOB_RECURSE SOURCES "src/*.cpp")
file(GLOB_RECURSE HEADERS "src/*.h")

# create executable file
add_executable(smt_parser_comparison src/main.cpp)

# include directories
target_include_directories(smt_parser_comparison PRIVATE 
    ${CMAKE_SOURCE_DIR}/SMTParser/include
    ${CMAKE_SOURCE_DIR}/src
    ${GMP_INCLUDE_DIRS}
    ${GMPXX_INCLUDE_DIRS}
)

# link libraries
target_link_libraries(smt_parser_comparison PRIVATE 
    smt_parser_lib  # from src directory
    smtparser_static  # SMTParser library
    ${GMP_LIBRARIES}
    ${GMPXX_LIBRARIES}
)

# set output directories
# set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
# set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
# set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# install rules
install(TARGETS smt_parser_comparison DESTINATION bin)

# install header files
install(DIRECTORY src/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
) 