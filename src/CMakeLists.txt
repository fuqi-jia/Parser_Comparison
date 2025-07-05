cmake_minimum_required(VERSION 3.10)

# 添加源文件
set(SOURCES 
    main.cpp
    smt_parser_comparison.cpp
)

# 添加头文件
set(HEADERS
    smt_parser_comparison.h
)

# 包含SMTParser头文件目录
include_directories(${CMAKE_SOURCE_DIR}/SMTParser/include)

# 添加可执行文件
add_library(smt_parser_lib STATIC smt_parser_comparison.cpp)

# 链接SMTParser库
target_link_libraries(smt_parser_lib PUBLIC smtparser_static)

# 如果在Linux系统上，需要链接额外的库
if(UNIX AND NOT APPLE)
    target_link_libraries(smt_parser_lib PUBLIC stdc++fs)
endif()

# 设置包含目录
target_include_directories(smt_parser_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# 查找文件系统库（C++17标准）
find_package(Threads REQUIRED)
target_link_libraries(smt_parser_lib PUBLIC Threads::Threads) 