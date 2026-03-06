set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_library(LIBRT rt)

# 支持三种 CVC5 布局：源码构建（含 build/）、预编译静态包（lib/*.a）、或安装目录（lib/*.so，如 cvc5-install）
set(CVC5_PREBUILT FALSE)
set(CVC5_SHARED_INSTALL FALSE)
if (EXISTS "${CVC5_HOME}/include/cvc5/cvc5.h")
  if (EXISTS "${CVC5_HOME}/lib/libcvc5.a")
    set(CVC5_PREBUILT TRUE)
    message(STATUS "CVC5: 使用预编译静态包 ${CVC5_HOME}")
  elseif (EXISTS "${CVC5_HOME}/lib/libcvc5.so" OR EXISTS "${CVC5_HOME}/lib/libcvc5.so.1")
    set(CVC5_PREBUILT TRUE)
    set(CVC5_SHARED_INSTALL TRUE)
    message(STATUS "CVC5: 使用安装目录（共享库）${CVC5_HOME}")
  endif()
endif()

add_library(smt-switch-cvc5 "${SMT_SWITCH_LIB_TYPE}"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cvc5_datatype.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cvc5_factory.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cvc5_solver.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cvc5_sort.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/cvc5_term.cpp"
  )
target_include_directories (smt-switch-cvc5 PUBLIC "${PROJECT_SOURCE_DIR}/include")
target_include_directories (smt-switch-cvc5 PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_include_directories (smt-switch-cvc5 PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/cvc5/include")
target_include_directories (smt-switch-cvc5 PUBLIC "${CVC5_HOME}/include")
if (NOT CVC5_PREBUILT)
  target_include_directories (smt-switch-cvc5 PUBLIC "${CVC5_HOME}/src")
  target_include_directories (smt-switch-cvc5 PUBLIC "${CVC5_HOME}/build/include")
endif()
target_include_directories (smt-switch-cvc5 PUBLIC ${GMP_INCLUDE_DIR})

if (LIBRT)
  target_link_libraries(smt-switch-cvc5 ${LIBRT})
endif()

if (CVC5_PREBUILT)
  set(CVC5_LIB_DIR "${CVC5_HOME}/lib")
  if (CVC5_SHARED_INSTALL)
    # cvc5-install 从源码 make install 得到：libcvc5.so, libcvc5parser.so, libpoly.so, libpolyxx.so；gmp/gmpxx 可能来自 Conda/系统
    find_library(CVC5_LIB REQUIRED NAMES cvc5 PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(CVC5PARSER_LIB REQUIRED NAMES cvc5parser PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(POLYLIB REQUIRED NAMES poly PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(POLYLIBXX REQUIRED NAMES polyxx PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(GMP_LIB_REQUIRED REQUIRED NAMES gmp)
    find_library(GMPXX_LIB_REQUIRED REQUIRED NAMES gmpxx)
    target_link_directories(smt-switch-cvc5 PRIVATE "${CVC5_LIB_DIR}")
    target_link_libraries(smt-switch-cvc5 ${CVC5_LIB} ${CVC5PARSER_LIB} ${POLYLIBXX} ${POLYLIB} ${GMPXX_LIB_REQUIRED} ${GMP_LIB_REQUIRED})
    # $ORIGIN/.. 使加载时在父目录找到 libsmt-switch.so（cvc5/ 与 libsmt-switch.so 同级的上一级）
    set_target_properties(smt-switch-cvc5 PROPERTIES INSTALL_RPATH "${CVC5_LIB_DIR};\$ORIGIN/.." BUILD_WITH_INSTALL_RPATH TRUE)
  else()
    find_library(POLYLIB REQUIRED NAMES picpoly PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(POLYLIBXX REQUIRED NAMES picpolyxx PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(CADICAL REQUIRED NAMES cadical PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(GMP_LIB_REQUIRED REQUIRED NAMES gmp PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(GMPXX_LIB_REQUIRED REQUIRED NAMES gmpxx PATHS "${CVC5_LIB_DIR}" NO_DEFAULT_PATH)
    target_link_libraries(smt-switch-cvc5 "${CVC5_LIB_DIR}/libcvc5.a" "${CVC5_LIB_DIR}/libcvc5parser.a")
    target_link_libraries(smt-switch-cvc5 ${POLYLIBXX} ${POLYLIB} ${CADICAL} ${GMPXX_LIB_REQUIRED} ${GMP_LIB_REQUIRED})
  endif()
else()
  find_library(POLYLIB REQUIRED
               NAMES libpicpoly.a
               PATHS "${CVC5_HOME}/build/deps/lib")
  find_library(POLYLIBXX REQUIRED
               NAMES libpicpolyxx.a
               PATHS "${CVC5_HOME}/build/deps/lib")
  find_library(CADICAL REQUIRED
               NAMES libcadical.a libcadical.so libcadical.dylib
               )
  target_link_libraries(smt-switch-cvc5 "${CVC5_HOME}/build/src/libcvc5.a")
  target_link_libraries(smt-switch-cvc5 "${CVC5_HOME}/build/src/parser/libcvc5parser.a")
  target_link_libraries(smt-switch-cvc5 ${POLYLIBXX} ${POLYLIB} ${CADICAL})
  target_link_libraries(smt-switch-cvc5 ${GMP_LIBRARIES})
endif()

target_link_libraries(smt-switch-cvc5 smt-switch)
if (NOT CVC5_PREBUILT)
  target_link_libraries(smt-switch-cvc5 ${GMP_LIBRARIES})
endif()

# 使 libsmt-switch-cvc5.so 在运行时能找到上一级的 libsmt-switch.so，无需 LD_LIBRARY_PATH
if(NOT CVC5_SHARED_INSTALL)
  set_target_properties(smt-switch-cvc5 PROPERTIES
    BUILD_RPATH "\$ORIGIN/.."
    INSTALL_RPATH "\$ORIGIN/.."
    BUILD_WITH_INSTALL_RPATH FALSE)
endif()

if (SMT_SWITCH_LIB_TYPE STREQUAL STATIC AND NOT CVC5_PREBUILT)
  # we want the static library to include the cvc5 source and dependencies (except GMP)
  # use libtool to combine
  add_custom_command(
    OUTPUT static-smt-switch-cvc5.stamp
    COMMAND
      mkdir ssc-working && cd ssc-working &&
      # create new static library that combines them all
      ${PROJECT_SOURCE_DIR}/scripts/repack-static-lib.sh "$<TARGET_FILE_NAME:smt-switch-cvc5>" "${CVC5_HOME}/build/src/libcvc5.a" "${POLYLIBXX}" "${POLYLIB}" "${CADICAL}" "../$<TARGET_FILE_NAME:smt-switch-cvc5>" &&
      # replace the original one
      mv "$<TARGET_FILE_NAME:smt-switch-cvc5>" "../$<TARGET_FILE_NAME:smt-switch-cvc5>" &&
      # now clean up the temporary directory
      cd ../ && rm -rf ssc-working
    COMMAND ${CMAKE_COMMAND} -E touch static-smt-switch-cvc5.stamp
    DEPENDS
      smt-switch-cvc5
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    VERBATIM
    )

  add_custom_target(
    repack-cvc5-static-lib ALL
    DEPENDS static-smt-switch-cvc5.stamp
    )
endif()

install(TARGETS smt-switch-cvc5 DESTINATION lib)
# install headers -- for expert use only
install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/include/"
  DESTINATION include/smt-switch
  FILES_MATCHING PATTERN "*.h")
