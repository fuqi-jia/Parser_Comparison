cmake_minimum_required(VERSION 3.10)

# This subdirectory only takes effect when -DBUILD_RDL_CASE_STUDY=ON; the top-
# level Parser_Comparison CMakeLists.txt is the only place that should call
# add_subdirectory() for it.

find_package(PkgConfig REQUIRED)
pkg_check_modules(GMP REQUIRED gmp)
pkg_check_modules(GMPXX REQUIRED gmpxx)

add_executable(somt-rdl-adapter main.cpp)

target_include_directories(somt-rdl-adapter PRIVATE
    ${CMAKE_SOURCE_DIR}/SOMTParser/include
    ${GMP_INCLUDE_DIRS}
    ${GMPXX_INCLUDE_DIRS}
)

target_link_libraries(somt-rdl-adapter PRIVATE
    somtparser_static
    ${GMPXX_LIBRARIES}
    ${GMP_LIBRARIES}
)
