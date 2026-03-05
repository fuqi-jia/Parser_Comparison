# smt_switch_parser：使用 smt-switch 的 SmtLibReader 解析 SMT-LIB 并输出 JSON。
# 方式一：在 smt-switch-1.0.6 下编译（需 bison/flex、CVC5_HOME 指向 cvc5 源码目录）：
#   cd smt-switch-1.0.6 && mkdir build && cd build
#   cmake .. -DSMTLIB_READER=ON -DBUILD_CVC5=ON -DCVC5_HOME=/path/to/cvc5
#   make
# 得到 smt-switch-1.0.6/build/smt_switch_parser（或 build/smt-switch-1.0.6/smt_switch_parser）
#
# 方式二：从本目录 add_subdirectory 构建（同上，需 CVC5_HOME）：
#   mkdir build && cd build
#   cmake .. -DSMTLIB_READER=ON -DBUILD_CVC5=ON -DCVC5_HOME=/path/to/cvc5
#   make
# 得到 build/smt-switch-1.0.6/smt_switch_parser
cmake_minimum_required(VERSION 3.14)
project(smt_switch_parser_build NONE)

set(CMAKE_CXX_STANDARD 17)

# 可选：通过 smt-switch-1.0.6 构建（需 SMTLIB_READER=ON, BUILD_CVC5=ON, CVC5_HOME）
if(SMTLIB_READER AND BUILD_CVC5 AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/smt-switch-1.0.6/CMakeLists.txt")
  set(BUILD_BTOR OFF CACHE BOOL "" FORCE)
  set(BUILD_BITWUZLA OFF CACHE BOOL "" FORCE)
  set(BUILD_MSAT OFF CACHE BOOL "" FORCE)
  set(BUILD_YICES2 OFF CACHE BOOL "" FORCE)
  set(BUILD_Z3 OFF CACHE BOOL "" FORCE)
  set(BUILD_TESTS OFF CACHE BOOL "" FORCE)
  add_subdirectory(smt-switch-1.0.6 ${CMAKE_BINARY_DIR}/smt-switch-1.0.6)
  # smt_switch_parser 目标由 smt-switch-1.0.6 在 SMTLIB_READER+BUILD_CVC5 时注册
endif()
