# cvc5_parser：链接 cvc5 C API 解析 SMT-LIB，输出 JSON（含 ast_node_count）
cmake_minimum_required(VERSION 3.10)
project(cvc5_parser CXX)

set(CMAKE_CXX_STANDARD 17)

# 本目录下预编译包：cvc5-Linux-* 或 cvc5-*-*（多为 libcxx-static，需 clang -stdlib=libc++ 或使用系统/自编 cvc5）
file(GLOB CVC5_PREBUILT "cvc5-Linux-*" "cvc5-*-*")
if(CVC5_PREBUILT)
    list(GET CVC5_PREBUILT 0 CVC5_DIR)
    set(CVC5_INCLUDE "${CVC5_DIR}/include")
    set(CVC5_LIB "${CVC5_DIR}/lib")
    # 预编译包通常含 libcvc5.a + libcvc5parser.a，依赖 GMP、libpicpoly、cadical；若为 libcxx-static 则需 clang -stdlib=libc++
    set(CVC5_LIBS cvc5 cvc5parser picpolyxx picpoly cadical gmpxx gmp)
else()
    set(CVC5_INCLUDE "${CMAKE_CURRENT_SOURCE_DIR}/include")
    set(CVC5_LIB "${CMAKE_CURRENT_SOURCE_DIR}/lib")
    set(CVC5_LIBS cvc5 cvc5parser picpolyxx picpoly cadical gmpxx gmp)
endif()

add_executable(cvc5_parser cvc5_parser.cpp)
target_include_directories(cvc5_parser PRIVATE ${CVC5_INCLUDE})
target_link_directories(cvc5_parser PRIVATE ${CVC5_LIB})
target_link_libraries(cvc5_parser PRIVATE ${CVC5_LIBS})
# 若使用 libcxx-static 预编译包，请用 clang 并加：-DCMAKE_CXX_FLAGS="-stdlib=libc++" -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++"
target_compile_options(cvc5_parser PRIVATE -O2 -Wall)

install(TARGETS cvc5_parser RUNTIME DESTINATION bin)
