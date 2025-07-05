cmake_minimum_required(VERSION 3.10)
project(SMTLIBParser_Test)

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

# add SMTParser subdirectory
add_subdirectory(SMTLIBParser)

# find GMP library
find_package(PkgConfig REQUIRED)
pkg_check_modules(GMP REQUIRED gmp)
pkg_check_modules(GMPXX REQUIRED gmpxx)

# get all source files
file(GLOB_RECURSE SOURCES "src/*.cpp")
file(GLOB_RECURSE HEADERS "src/*.h")

# create executable file
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

# include directories
target_include_directories(${PROJECT_NAME} PRIVATE 
    ${CMAKE_SOURCE_DIR}/SMTLIBParser/include
    ${CMAKE_SOURCE_DIR}/src
    ${GMP_INCLUDE_DIRS}
    ${GMPXX_INCLUDE_DIRS}
)

# link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE 
    smtlibparser_static  # SMTLIBParser library
    ${GMP_LIBRARIES}
    ${GMPXX_LIBRARIES}
)

# set output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# install rules
install(TARGETS ${PROJECT_NAME}
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

# install header files
install(DIRECTORY src/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
) 