cmake_minimum_required(VERSION 3.10)

project(SMT_Parser_Comparison VERSION 1.0)

# 设置C++标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

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
add_executable(smt_parser_comparison ${SOURCES} ${HEADERS})

# 查找文件系统库（C++17标准）
find_package(Threads REQUIRED)
target_link_libraries(smt_parser_comparison PRIVATE Threads::Threads)

# 如果在Linux系统上，需要链接额外的库
if(UNIX AND NOT APPLE)
    target_link_libraries(smt_parser_comparison PRIVATE stdc++fs)
endif()

# 链接SMTParser库
target_link_libraries(smt_parser_comparison PRIVATE smtparser_static)

# 安装目标
install(TARGETS smt_parser_comparison DESTINATION bin) 