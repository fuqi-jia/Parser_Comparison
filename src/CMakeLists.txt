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

# 包含 SOMTParser 头文件目录
include_directories(${CMAKE_SOURCE_DIR}/SOMTParser/include)

# 添加库文件
add_library(smt_parser_lib STATIC
    smt_parser_comparison.cpp
    process_runner.cpp
    metrics_collector.cpp
    benchmark_runner.cpp
    report_writer.cpp
)

# 链接SMTParser库
target_link_libraries(smt_parser_lib PUBLIC somtparser_static)

# 如果在Linux系统上，需要链接额外的库
if(UNIX AND NOT APPLE)
    target_link_libraries(smt_parser_lib PUBLIC stdc++fs)
endif()

# 设置包含目录
target_include_directories(smt_parser_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# 查找文件系统库（C++17标准）
find_package(Threads REQUIRED)
target_link_libraries(smt_parser_lib PUBLIC Threads::Threads)

# 添加parser_wrapper可执行程序
add_executable(smt_parser_wrapper parser_wrapper.cpp)
target_link_libraries(smt_parser_wrapper PUBLIC somtparser_static)

# 如果在Linux系统上，需要链接额外的库
if(UNIX AND NOT APPLE)
    target_link_libraries(smt_parser_wrapper PUBLIC stdc++fs)
endif()

# 查找文件系统库（C++17标准）
target_link_libraries(smt_parser_wrapper PUBLIC Threads::Threads)

# 将smt_parser_wrapper复制到构建目录的根目录
add_custom_command(
    TARGET smt_parser_wrapper POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy 
        $<TARGET_FILE:smt_parser_wrapper> 
        ${CMAKE_BINARY_DIR}/smt_parser_wrapper
    COMMENT "Copying smt_parser_wrapper to build directory root"
)

add_executable(roundtrip_tool roundtrip_tool.cpp)
target_link_libraries(roundtrip_tool PUBLIC somtparser_static)
if(UNIX AND NOT APPLE)
    target_link_libraries(roundtrip_tool PUBLIC stdc++fs)
endif()
target_link_libraries(roundtrip_tool PUBLIC Threads::Threads)
add_custom_command(
    TARGET roundtrip_tool POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        $<TARGET_FILE:roundtrip_tool>
        ${CMAKE_BINARY_DIR}/roundtrip_tool
    COMMENT "Copying roundtrip_tool to build directory root"
)