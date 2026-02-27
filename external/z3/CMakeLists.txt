# Z3 Parser：输出本对比工具期望的 JSON，可单独编译
cmake_minimum_required(VERSION 3.10)
project(z3_parser CXX)

set(CMAKE_CXX_STANDARD 17)

# 自动检测 Z3：优先预编译包 z3-*-x64-*，否则 z3-z3-*
file(GLOB Z3_PREBUILT "z3-*-x64-*")
file(GLOB Z3_SRC "z3-z3-*")
if(Z3_PREBUILT)
    list(GET Z3_PREBUILT 0 Z3_DIR)
    set(Z3_INCLUDE "${Z3_DIR}/include")
    set(Z3_LIB "${Z3_DIR}/lib")
elseif(Z3_SRC)
    list(GET Z3_SRC 0 Z3_DIR)
    set(Z3_INCLUDE "${Z3_DIR}/src/api/c++;${Z3_DIR}/src/api")
    set(Z3_LIB "${Z3_DIR}/build")
else()
    set(Z3_INCLUDE "/usr/include")
    set(Z3_LIB "/usr/lib")
endif()

add_executable(z3_parser z3_parser.cpp)
target_include_directories(z3_parser PRIVATE ${Z3_INCLUDE})
target_link_directories(z3_parser PRIVATE ${Z3_LIB})
target_link_libraries(z3_parser PRIVATE z3)
target_compile_options(z3_parser PRIVATE -O2 -Wall)

install(TARGETS z3_parser RUNTIME DESTINATION bin)
