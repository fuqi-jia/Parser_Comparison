#!/usr/bin/env bash
# 一键编译 external 下所有 parser（各目录独立构建，失败不中断其余）
# 用法: ./scripts/build_all_parsers.sh [external 目录，默认 REPO_ROOT/external]
# 可选环境变量:
#   CVC5_HOME   - 编译 smt-switch 时需指向 cvc5 源码根目录
#   USE_CLANG_LIBCXX - 设为 1 时，cvc5_parser 使用 clang -stdlib=libc++（适配 libcxx-static 预编译包）
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTERNAL_ROOT="${1:-$REPO_ROOT/external}"
cd "$EXTERNAL_ROOT"
NPROC="$(nproc 2>/dev/null || echo 1)"
OK=()
FAIL=()
SKIP=()

run_build() {
    local name="$1"
    local dir="$2"
    shift 2
    if [ ! -d "$dir" ]; then
        echo "[SKIP] $name: 目录不存在 $dir"
        SKIP+=("$name")
        return 0
    fi
    echo "-------- Building $name ($dir) --------"
    if (cd "$dir" && "$@"); then
        echo "[OK] $name"
        OK+=("$name")
        return 0
    else
        echo "[FAIL] $name"
        FAIL+=("$name")
        return 1
    fi
}

# cvc5: cvc5_parser (CMake + make)。预编译包名含 libcxx 时自动用 clang+libc++
build_cvc5() {
    if [ ! -f "$EXTERNAL_ROOT/cvc5/CMakeLists.txt" ]; then
        echo "[SKIP] cvc5: external/cvc5 缺少 CMakeLists.txt"
        echo "       请从仓库或本机同步 external/cvc5 下的 CMakeLists.txt、cvc5_parser.cpp、run.sh 等（预编译包 cvc5-Linux-*-libcxx-static 需单独解压到该目录）"
        SKIP+=("cvc5")
        return
    fi
    if [ ! -f "$EXTERNAL_ROOT/cvc5/cvc5_parser.cpp" ]; then
        echo "[SKIP] cvc5: 无 cvc5_parser.cpp"
        SKIP+=("cvc5")
        return
    fi
    use_libcxx="${USE_CLANG_LIBCXX:-0}"
    if [ "$use_libcxx" != "1" ] && ls "$EXTERNAL_ROOT/cvc5"/cvc5-*libcxx* 1>/dev/null 2>&1 && command -v clang++ &>/dev/null; then
        use_libcxx=1
    fi
    if [ "$use_libcxx" != "1" ] && ls "$EXTERNAL_ROOT/cvc5"/cvc5-*libcxx* 1>/dev/null 2>&1; then
        echo "[SKIP] cvc5: 预编译包为 libcxx，需安装 clang++ 或设置 USE_CLANG_LIBCXX=1"
        SKIP+=("cvc5")
        return
    fi
    if ( cd "$EXTERNAL_ROOT/cvc5" && mkdir -p build && cd build && \
         if [ "$use_libcxx" = "1" ]; then
             cmake .. -DCMAKE_CXX_COMPILER=clang++ \
                 -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
                 -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++"
         else
             cmake ..
         fi && \
         make -j"$NPROC" ); then
        echo "[OK] cvc5"
        OK+=("cvc5")
    else
        echo "[FAIL] cvc5"
        FAIL+=("cvc5")
    fi
}

# z3: z3_parser (Makefile)
build_z3() {
    run_build "z3" "z3" make -j"$NPROC"
}

# antlr4_parser: Java (make)。无 SMTLIBv2.g4 时跳过
build_antlr4() {
    if [ ! -d "$EXTERNAL_ROOT/antlr4_parser" ] || [ ! -f "$EXTERNAL_ROOT/antlr4_parser/antlr4_parser.java" ]; then
        echo "[SKIP] antlr4_parser: 目录或 antlr4_parser.java 不存在"
        SKIP+=("antlr4_parser")
        return
    fi
    ad="$EXTERNAL_ROOT/antlr4_parser"
    if [ ! -f "$ad/SMTLIBv2.g4" ] && [ ! -f "$ad/smtlibv2-grammar-master/src/main/resources/SMTLIBv2.g4" ] && [ ! -f "$ad/smtlibv2-grammar/src/main/resources/SMTLIBv2.g4" ]; then
        echo "[SKIP] antlr4_parser: 未找到 SMTLIBv2.g4"
        SKIP+=("antlr4_parser")
        return
    fi
    if ( cd "$ad" && ( make -j"$NPROC" 2>/dev/null || ( make generate 2>/dev/null; make -j"$NPROC" ) ) ); then
        echo "[OK] antlr4_parser"
        OK+=("antlr4_parser")
    else
        echo "[FAIL] antlr4_parser"
        FAIL+=("antlr4_parser")
    fi
}

# jsmtlib: build.sh
build_jsmtlib() {
    run_build "jsmtlib" "jsmtlib" bash ./build.sh
}

# haskell-0.0.2: cabal。未安装 cabal 时视为 SKIP
build_haskell() {
    if [ ! -d "$EXTERNAL_ROOT/haskell-0.0.2" ] || [ ! -f "$EXTERNAL_ROOT/haskell-0.0.2/build.sh" ]; then
        echo "[SKIP] haskell-0.0.2: 目录或 build.sh 不存在"
        SKIP+=("haskell-0.0.2")
        return
    fi
    if ! command -v cabal &>/dev/null; then
        echo "[SKIP] haskell-0.0.2: 未找到 cabal"
        echo "       安装: 推荐 ghcup（https://www.haskell.org/ghcup/），或 Ubuntu/Debian: sudo apt install ghc cabal-install"
        SKIP+=("haskell-0.0.2")
        return
    fi
    run_build "haskell-0.0.2" "haskell-0.0.2" bash ./build.sh
}

# smt-switch: 需 CVC5_HOME 或自动检测：优先用 external/cvc5 下预编译包，否则用 external/smt-switch/src/cvc5（cvc5 源码）
build_smt_switch() {
    if [ -z "${CVC5_HOME:-}" ]; then
        # 优先：cvc5 预编译包（include + lib，无需先编译 cvc5）
        PREBUILT=$(ls -d "$EXTERNAL_ROOT/cvc5"/cvc5-* 2>/dev/null | head -1)
        if [ -n "$PREBUILT" ] && [ -f "$PREBUILT/lib/libcvc5.a" ] && [ -f "$PREBUILT/include/cvc5/cvc5.h" ]; then
            CVC5_HOME="$PREBUILT"
            echo "[smt-switch] 使用 cvc5 预编译包: $CVC5_HOME"
        # 否则：本仓库内 cvc5 源码（需已在该目录执行过 cmake+make）
        elif [ -f "$EXTERNAL_ROOT/smt-switch/src/cvc5/CMakeLists.txt" ]; then
            CVC5_HOME="$EXTERNAL_ROOT/smt-switch/src/cvc5"
            if [ ! -f "$CVC5_HOME/build/src/libcvc5.a" ]; then
                echo "[SKIP] smt-switch: 检测到 cvc5 源码但尚未构建"
                echo "       请先构建 cvc5: cd $CVC5_HOME && mkdir -p build && cd build && cmake .. && make -j\$(nproc)"
                echo "       或使用预编译包：将 cvc5-Linux-*-libcxx-static 解压到 $EXTERNAL_ROOT/cvc5/ 后重试"
                SKIP+=("smt-switch")
                return
            fi
            echo "[smt-switch] 使用已构建的 cvc5 源码: $CVC5_HOME"
        else
            echo "[SKIP] smt-switch: 未设置 CVC5_HOME"
            echo "       需安装: bison, flex（Ubuntu/Debian: sudo apt install bison flex）"
            echo "       需设置: CVC5_HOME 指向 cvc5 源码根目录，或将 cvc5 预编译包解压到 $EXTERNAL_ROOT/cvc5/ 或将 cvc5 源码解压到 $EXTERNAL_ROOT/smt-switch/src/cvc5"
            echo "       然后: CVC5_HOME=/path/to/cvc5 $SCRIPT_DIR/build_all_parsers.sh"
            SKIP+=("smt-switch")
            return
        fi
    fi
    if [ ! -d "$EXTERNAL_ROOT/smt-switch/smt-switch-1.0.6" ]; then
        echo "[SKIP] smt-switch: 无 smt-switch-1.0.6 目录"
        SKIP+=("smt-switch")
        return
    fi
    # 预编译包为 libcxx 时需 clang+libc++（仅设置 CXX，避免 C 编译器测试收到 -stdlib=libc++）
    EXTRA_CMAKE=""
    if [ -f "${CVC5_HOME}/lib/libcvc5.a" ] && echo "$CVC5_HOME" | grep -q libcxx && command -v clang++ &>/dev/null; then
        EXTRA_CMAKE="-DCMAKE_CXX_COMPILER=clang++ -DCMAKE_CXX_FLAGS=-stdlib=libc++"
    fi
    if ( cd "$EXTERNAL_ROOT/smt-switch" && mkdir -p build && cd build && \
         cmake .. \
             -DSMTLIB_READER=ON \
             -DBUILD_CVC5=ON \
             -DCVC5_HOME="${CVC5_HOME}" \
             -DBUILD_BTOR=OFF \
             -DBUILD_BITWUZLA=OFF \
             -DBUILD_MSAT=OFF \
             -DBUILD_YICES2=OFF \
             -DBUILD_Z3=OFF \
             -DBUILD_TESTS=OFF \
             $EXTRA_CMAKE && \
         make -j"$NPROC" ); then
        echo "[OK] smt-switch"
        OK+=("smt-switch")
    else
        echo "[FAIL] smt-switch"
        FAIL+=("smt-switch")
    fi
}

# pysmt / prolog-smtlib: 无编译步骤
echo "=============================================="
echo "  Parser_Comparison external — 一键编译"
echo "  EXTERNAL_ROOT = $EXTERNAL_ROOT"
echo "  NPROC = $NPROC"
echo "=============================================="

build_cvc5
build_z3
build_antlr4
build_jsmtlib
build_haskell
build_smt_switch

echo "=============================================="
echo "  汇总"
echo "=============================================="
printf "  成功: %s — %s\n" "${#OK[@]}" "${OK[*]:-无}"
printf "  失败: %s — %s\n" "${#FAIL[@]}" "${FAIL[*]:-无}"
printf "  跳过: %s — %s\n" "${#SKIP[@]}" "${SKIP[*]:-无}"
echo "=============================================="
echo "说明: pysmt / prolog-smtlib 为脚本或库，无需编译。"
echo "      cvc5 预编译包为 libcxx 时需 clang++ 与 libc++，或: USE_CLANG_LIBCXX=1 $SCRIPT_DIR/build_all_parsers.sh"
echo "      若被跳过："
echo "        haskell-0.0.2 — 安装 GHC + Cabal（ghcup 或 apt install ghc cabal-install）及 alex（cabal install alex 或 apt install alex）"
echo "        smt-switch    — 安装 bison/flex，并设置 CVC5_HOME 指向 cvc5 源码根目录"
echo "=============================================="

if [ ${#FAIL[@]} -gt 0 ]; then
    exit 1
fi
exit 0
