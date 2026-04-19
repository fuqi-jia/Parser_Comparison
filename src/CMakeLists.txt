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

# --- native_z3_dual_path: SOMTParser dump + Z3 on original vs dump (needs Z3 next to external/z3 or system) ---
set(Z3_DUAL_FOUND FALSE)
set(Z3_DUAL_INCLUDE "")
set(Z3_DUAL_LIB "")
file(GLOB Z3_DUAL_PREBUILT "${CMAKE_SOURCE_DIR}/external/z3/z3-*-x64-*")
file(GLOB Z3_DUAL_SRC "${CMAKE_SOURCE_DIR}/external/z3/z3-z3-*")
if(Z3_DUAL_PREBUILT)
    list(GET Z3_DUAL_PREBUILT 0 _Z3D)
    if(EXISTS "${_Z3D}/lib/libz3.so" OR EXISTS "${_Z3D}/lib/libz3.a")
        set(Z3_DUAL_INCLUDE "${_Z3D}/include")
        set(Z3_DUAL_LIB "${_Z3D}/lib")
        set(Z3_DUAL_FOUND TRUE)
    endif()
endif()
if(NOT Z3_DUAL_FOUND AND Z3_DUAL_SRC)
    list(GET Z3_DUAL_SRC 0 _Z3D)
    if(EXISTS "${_Z3D}/build/libz3.so" OR EXISTS "${_Z3D}/build/libz3.a")
        set(Z3_DUAL_INCLUDE "${_Z3D}/src/api/c++;${_Z3D}/src/api")
        set(Z3_DUAL_LIB "${_Z3D}/build")
        set(Z3_DUAL_FOUND TRUE)
    endif()
endif()
if(NOT Z3_DUAL_FOUND AND DEFINED ENV{CONDA_PREFIX})
    if(EXISTS "$ENV{CONDA_PREFIX}/lib/libz3.so" OR EXISTS "$ENV{CONDA_PREFIX}/lib/libz3.a")
        set(Z3_DUAL_LIB "$ENV{CONDA_PREFIX}/lib")
        set(Z3_DUAL_INCLUDE "$ENV{CONDA_PREFIX}/include")
        set(Z3_DUAL_FOUND TRUE)
    endif()
endif()
if(NOT Z3_DUAL_FOUND)
    find_library(Z3_DUAL_LIB_PATH NAMES z3)
    if(Z3_DUAL_LIB_PATH)
        get_filename_component(Z3_DUAL_LIB "${Z3_DUAL_LIB_PATH}" DIRECTORY)
        get_filename_component(_Z3P "${Z3_DUAL_LIB}" DIRECTORY)
        set(Z3_DUAL_INCLUDE "${_Z3P}/include")
        set(Z3_DUAL_FOUND TRUE)
    endif()
endif()

if(Z3_DUAL_FOUND)
    add_executable(native_z3_dual_path native_z3_dual_path.cpp)
    target_include_directories(native_z3_dual_path PRIVATE
        ${CMAKE_SOURCE_DIR}/SOMTParser/include
        ${Z3_DUAL_INCLUDE})
    target_link_directories(native_z3_dual_path PRIVATE ${Z3_DUAL_LIB})
    target_link_libraries(native_z3_dual_path PRIVATE somtparser_static z3 Threads::Threads)
    if(UNIX AND NOT APPLE)
        target_link_libraries(native_z3_dual_path PRIVATE stdc++fs)
    endif()
    add_custom_command(
        TARGET native_z3_dual_path POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
            $<TARGET_FILE:native_z3_dual_path>
            ${CMAKE_BINARY_DIR}/native_z3_dual_path
        COMMENT "Copying native_z3_dual_path to build directory root"
    )
    message(STATUS "native_z3_dual_path: Z3 include=${Z3_DUAL_INCLUDE} lib=${Z3_DUAL_LIB}")
else()
    message(STATUS "native_z3_dual_path: Z3 not found — skipping (install libz3 / conda, or prebuilt under external/z3)")
endif()