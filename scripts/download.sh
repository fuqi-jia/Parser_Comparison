#!/usr/bin/env bash
# 一键安装：external 下各 parser 所需依赖/源码下载 + SMT-LIB benchmark 下载与解压
# 用法: ./scripts/download.sh [--parsers-only] [--benchmark-only] [--theories QF_LIA,QF_BV,...]
# 下载来源:
#   cvc5:       https://github.com/cvc5/cvc5 (Releases 源码)
#   z3:         https://github.com/Z3Prover/z3 (Releases 源码)
#   smt-switch: https://github.com/stanford-centaur/smt-switch
#   haskell:    https://hackage.haskell.org/package/smt-lib-0.0.2/smt-lib-0.0.2.tar.gz
#   prolog:     https://github.com/jariazavalverde/prolog-smtlib
#   pysmt:      https://github.com/pysmt/pysmt (pip install pysmt)
#   antlr4:     setup.sh 内 wget smtlibv2-grammar + ANTLR jar
#   jSMTLIB:    https://github.com/smtlib/jSMTLIB
#   Benchmarks: https://zenodo.org/records/16740866 (SMT-LIB non-incremental)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTERNAL="$REPO_ROOT/external"
BENCHMARK="$REPO_ROOT/benchmark"
ZENODO_RECORD="16740866"
# 与 sample_benchmarks.py 默认 theory 一致
DEFAULT_THEORIES="QF_LIA,QF_LRA,QF_NIA,QF_NRA,QF_BV,QF_FP,QF_S,QF_AX"

# 各 parser 源码版本（可从 GitHub Releases 页更新）
CVC5_TAG="cvc5-1.3.3"
Z3_TAG="z3-4.16.0"
SMT_SWITCH_TAG="1.0.6"

DO_PARSERS=1
DO_BENCHMARK=1
THEORIES_STR="$DEFAULT_THEORIES"

while [ $# -gt 0 ]; do
    case "$1" in
        --parsers-only)   DO_BENCHMARK=0; shift ;;
        --benchmark-only) DO_PARSERS=0; shift ;;
        --theories)       THEORIES_STR="$2"; shift 2 ;;
        *) echo "未知选项: $1"; exit 1 ;;
    esac
done

THEORIES=($(echo "$THEORIES_STR" | tr ',' ' '))

download_url() {
    local url="$1"
    local out="$2"
    if [ -f "$out" ]; then
        echo "[已存在] $out"
        return 0
    fi
    if command -v wget &>/dev/null; then
        wget -q -O "$out" "$url" || { echo "wget 失败: $url"; rm -f "$out"; return 1; }
    elif command -v curl &>/dev/null; then
        curl -sL -o "$out" "$url" || { echo "curl 失败: $url"; rm -f "$out"; return 1; }
    else
        echo "需要 wget 或 curl"; exit 1
    fi
}

extract_tar_zst() {
    local arc="$1"
    local dest="$2"
    if [ ! -f "$arc" ]; then return 1; fi
    mkdir -p "$dest"
    if command -v zstd &>/dev/null; then
        zstd -d -c "$arc" | tar -xf - -C "$dest" && return 0
    fi
    if tar -xf "$arc" -I 'zstd -d' -C "$dest" 2>/dev/null; then
        return 0
    fi
    echo "需要 zstd 解压 .tar.zst（apt install zstd 或 dnf install zstd）"; return 1
}

extract_tar_gz() {
    local arc="$1"
    local dest="$2"
    if [ ! -f "$arc" ]; then return 1; fi
    mkdir -p "$dest"
    tar -xzf "$arc" -C "$dest" && return 0
    return 1
}

# ---------- Parsers ----------
do_parsers() {
    echo "=============================================="
    echo "  1. 下载 / 准备 external parsers"
    echo "=============================================="

    # ANTLR4 parser: smtlibv2-grammar + ANTLR jar（由 setup.sh 完成）
    if [ -d "$EXTERNAL/antlr4_parser" ]; then
        echo "-------- antlr4_parser (smtlibv2-grammar + ANTLR) --------"
        (cd "$EXTERNAL/antlr4_parser" && bash ./setup.sh) || echo "[跳过/失败] antlr4_parser setup"
    fi

    # jSMTLIB: 若缺少 jSMTLIB-0.9.10.1 则下载（https://github.com/smtlib/jSMTLIB）
    if [ -d "$EXTERNAL/jsmtlib" ] && [ ! -d "$EXTERNAL/jsmtlib/jSMTLIB-0.9.10.1" ]; then
        echo "-------- jSMTLIB (GitHub) --------"
        JSMTPATH="$EXTERNAL/jsmtlib"
        JSMTPACK="jSMTLIB-V0.9.10.1.zip"
        download_url "https://github.com/smtlib/jSMTLIB/archive/refs/tags/V0.9.10.1.zip" "$JSMTPATH/$JSMTPACK" && \
        (cd "$JSMTPATH" && unzip -o -q "$JSMTPACK" && [ -d jSMTLIB-V0.9.10.1 ] && mv jSMTLIB-V0.9.10.1 jSMTLIB-0.9.10.1; rm -f "$JSMTPACK") || true
    fi

    # cvc5: 优先下载预编译包（cvc5_parser 需要 include/lib）。仅有源码目录不算“已有预编译”，会继续尝试下载
    if [ -d "$EXTERNAL/cvc5" ]; then
        HAS_VALID_PREBUILT=""
        for d in $(ls -d "$EXTERNAL/cvc5"/cvc5-Linux-* "$EXTERNAL/cvc5"/cvc5-*-static 2>/dev/null); do
            [ -f "$d/include/cvc5/cvc5.h" ] && HAS_VALID_PREBUILT="$d" && break
        done
        if [ -n "$HAS_VALID_PREBUILT" ]; then
            echo "[已存在] cvc5 预编译包: $HAS_VALID_PREBUILT"
        elif [ -f "$EXTERNAL/cvc5/CMakeLists.txt" ]; then
            echo "-------- cvc5 预编译包 (GitHub Releases, Linux libcxx-static) --------"
            CVC5_DEST="$EXTERNAL/cvc5"
            CVC5_ARC="$CVC5_DEST/cvc5-prebuilt.tar.gz"
            # 若之前下载失败留下无效文件，删除以便重试（有效 gzip 才保留）
            if [ -f "$CVC5_ARC" ]; then
                if ! gzip -t "$CVC5_ARC" 2>/dev/null; then
                    rm -f "$CVC5_ARC"
                fi
            fi
            # 发布页见 https://github.com/cvc5/cvc5/releases ，尝试多种标签与资产名
            CVC5_DOWNLOADED=""
            for CVC5_RELEASE_TAG in "1.3.3" "cvc5-1.3.3"; do
              for CVC5_PREBUILT_NAME in \
                "cvc5-1.3.3-x86_64-Linux-libcxx-static.tar.gz" \
                "cvc5-1.3.3-x86_64-unknown-linux-gnu-libcxx-static.tar.gz" \
                "cvc5-Linux-x86_64-libcxx-static.tar.gz"; do
                if download_url "https://github.com/cvc5/cvc5/releases/download/${CVC5_RELEASE_TAG}/${CVC5_PREBUILT_NAME}" "$CVC5_ARC"; then
                  CVC5_DOWNLOADED=1
                  break 2
                fi
              done
            done
            if [ -n "$CVC5_DOWNLOADED" ] && [ -f "$CVC5_ARC" ]; then
                if gzip -t "$CVC5_ARC" 2>/dev/null && extract_tar_gz "$CVC5_ARC" "$CVC5_DEST"; then
                    rm -f "$CVC5_ARC"
                    echo "[OK] cvc5 预编译包已解压到 $EXTERNAL/cvc5/"
                else
                    rm -f "$CVC5_ARC"
                fi
            fi
            if ! ls -d "$EXTERNAL/cvc5"/cvc5-Linux-* "$EXTERNAL/cvc5"/cvc5-*-static 2>/dev/null | head -1 | grep -q .; then
                echo "[未获取] 请手动从 https://github.com/cvc5/cvc5/releases 下载 Linux libcxx-static 包，解压到 $EXTERNAL/cvc5/ 后执行 build_all_parsers.sh"
            fi
        else
            echo "-------- cvc5 源码 (GitHub Releases) --------"
            CVC5_ARC="$EXTERNAL/cvc5/cvc5-src.tar.gz"
            if download_url "https://github.com/cvc5/cvc5/archive/refs/tags/${CVC5_TAG}.tar.gz" "$CVC5_ARC"; then
                extract_tar_gz "$CVC5_ARC" "$EXTERNAL/cvc5" && rm -f "$CVC5_ARC" && echo "[OK] cvc5 源码已解压到 $EXTERNAL/cvc5/"
            fi
        fi
    fi

    # z3: 从 GitHub Releases 下载源码（https://github.com/Z3Prover/z3）
    if [ -d "$EXTERNAL/z3" ]; then
        if ! ls "$EXTERNAL/z3"/z3-* 2>/dev/null | head -1 | grep -q .; then
            echo "-------- z3 源码 (GitHub Releases) --------"
            Z3_ARC="$EXTERNAL/z3/z3-src.tar.gz"
            if download_url "https://github.com/Z3Prover/z3/archive/refs/tags/${Z3_TAG}.tar.gz" "$Z3_ARC"; then
                extract_tar_gz "$Z3_ARC" "$EXTERNAL/z3" && rm -f "$Z3_ARC" && echo "[OK] z3 源码已解压到 $EXTERNAL/z3/"
            fi
        else
            echo "[已存在] z3 源码或预编译包"
        fi
    fi

    # smt-switch: 从 GitHub 下载（https://github.com/stanford-centaur/smt-switch）
    if [ -d "$EXTERNAL/smt-switch" ] && [ ! -d "$EXTERNAL/smt-switch/smt-switch-${SMT_SWITCH_TAG}" ]; then
        echo "-------- smt-switch (GitHub) --------"
        SS_ARC="$EXTERNAL/smt-switch/smt-switch-src.tar.gz"
        # 若已有压缩包但未成功解压（损坏或不完整），删除以便重新下载
        if [ -f "$SS_ARC" ]; then
            if ! (gzip -t "$SS_ARC" 2>/dev/null); then
                echo "[移除损坏] $SS_ARC，将重新下载"
                rm -f "$SS_ARC"
            fi
        fi
        # 尝试 tag 1.0.6 或 v1.0.6（解压后目录均为 smt-switch-1.0.6）
        SS_DOWNLOADED=""
        for SS_TAG in "${SMT_SWITCH_TAG}" "v${SMT_SWITCH_TAG}"; do
            if download_url "https://github.com/stanford-centaur/smt-switch/archive/refs/tags/${SS_TAG}.tar.gz" "$SS_ARC"; then
                SS_DOWNLOADED=1
                break
            fi
        done
        if [ -n "$SS_DOWNLOADED" ]; then
            if extract_tar_gz "$SS_ARC" "$EXTERNAL/smt-switch"; then
                rm -f "$SS_ARC"
                if [ -d "$EXTERNAL/smt-switch/smt-switch-${SMT_SWITCH_TAG}" ]; then
                    echo "[OK] smt-switch 已解压"
                elif [ -d "$EXTERNAL/smt-switch/smt-switch-v${SMT_SWITCH_TAG}" ]; then
                    mv "$EXTERNAL/smt-switch/smt-switch-v${SMT_SWITCH_TAG}" "$EXTERNAL/smt-switch/smt-switch-${SMT_SWITCH_TAG}"
                    echo "[OK] smt-switch 已解压（已重命名为 smt-switch-${SMT_SWITCH_TAG}）"
                else
                    echo "[OK] smt-switch 已解压"
                fi
            else
                echo "[失败] 解压 smt-switch 失败，可删除 $SS_ARC 后重新运行本脚本"
            fi
        fi
    else
        [ -d "$EXTERNAL/smt-switch" ] && echo "[已存在] smt-switch"
    fi

    # haskell smt-lib: Hackage（https://hackage.haskell.org/package/smt-lib-0.0.2）
    if [ -d "$EXTERNAL/haskell-0.0.2" ]; then
        if [ ! -f "$EXTERNAL/haskell-0.0.2/smt-lib.cabal" ] && [ ! -f "$EXTERNAL/haskell-0.0.2/smt-lib-0.0.2.cabal" ]; then
            echo "-------- haskell smt-lib (Hackage) --------"
            HASK_ARC="$EXTERNAL/haskell-0.0.2/smt-lib-0.0.2.tar.gz"
            if download_url "https://hackage.haskell.org/package/smt-lib-0.0.2/smt-lib-0.0.2.tar.gz" "$HASK_ARC"; then
                extract_tar_gz "$HASK_ARC" "$EXTERNAL/haskell-0.0.2"
                if [ -d "$EXTERNAL/haskell-0.0.2/smt-lib-0.0.2" ]; then
                    mv "$EXTERNAL/haskell-0.0.2/smt-lib-0.0.2"/* "$EXTERNAL/haskell-0.0.2/"
                    rmdir "$EXTERNAL/haskell-0.0.2/smt-lib-0.0.2" 2>/dev/null || true
                fi
                rm -f "$HASK_ARC"
                echo "[OK] haskell smt-lib 已解压到 $EXTERNAL/haskell-0.0.2/"
            fi
        else
            echo "[已存在] haskell smt-lib"
        fi
    fi

    # prolog-smtlib: GitHub（https://github.com/jariazavalverde/prolog-smtlib）
    if [ -d "$EXTERNAL/prolog-smtlib" ] && [ ! -d "$EXTERNAL/prolog-smtlib/prolog" ]; then
        echo "-------- prolog-smtlib (GitHub) --------"
        if command -v git &>/dev/null; then
            TMP_PL="$EXTERNAL/prolog-smtlib.git.tmp"
            rm -rf "$TMP_PL"
            if git clone --depth 1 https://github.com/jariazavalverde/prolog-smtlib.git "$TMP_PL" 2>/dev/null; then
                cp -r "$TMP_PL"/prolog "$TMP_PL"/pack.pl "$TMP_PL"/README.md "$EXTERNAL/prolog-smtlib/" 2>/dev/null || true
                rm -rf "$TMP_PL"
                echo "[OK] prolog-smtlib 已克隆到 $EXTERNAL/prolog-smtlib/"
            else
                rm -rf "$TMP_PL"
                download_url "https://github.com/jariazavalverde/prolog-smtlib/archive/refs/heads/master.zip" "$EXTERNAL/prolog-smtlib/master.zip" && \
                (cd "$EXTERNAL/prolog-smtlib" && unzip -o -q master.zip && mv prolog-smtlib-master/prolog prolog-smtlib-master/pack.pl . 2>/dev/null; rm -rf prolog-smtlib-master master.zip) && echo "[OK] prolog-smtlib"
            fi
        else
            download_url "https://github.com/jariazavalverde/prolog-smtlib/archive/refs/heads/master.zip" "$EXTERNAL/prolog-smtlib/master.zip" && \
            (cd "$EXTERNAL/prolog-smtlib" && unzip -o -q master.zip && mv prolog-smtlib-master/prolog prolog-smtlib-master/pack.pl . 2>/dev/null; rm -rf prolog-smtlib-master master.zip) && echo "[OK] prolog-smtlib"
        fi
    else
        [ -d "$EXTERNAL/prolog-smtlib/prolog" ] && echo "[已存在] prolog-smtlib"
    fi

    # pysmt: pip 安装（https://github.com/pysmt/pysmt）
    echo "-------- pysmt (pip) --------"
    if command -v pip3 &>/dev/null; then
        pip3 install --user pysmt 2>/dev/null || pip3 install pysmt 2>/dev/null && echo "[OK] pysmt (pip3 install pysmt)" || echo "[跳过] pysmt 安装失败，可手动: pip3 install pysmt"
    elif command -v pip &>/dev/null; then
        pip install --user pysmt 2>/dev/null || pip install pysmt 2>/dev/null && echo "[OK] pysmt (pip install pysmt)" || echo "[跳过] pysmt 安装失败，可手动: pip install pysmt"
    else
        echo "[跳过] 未找到 pip/pip3，请手动: pip install pysmt"
    fi
    echo ""
}

# ---------- Benchmark (Zenodo SMT-LIB non-incremental) ----------
do_benchmark() {
    echo "=============================================="
    echo "  2. 下载 SMT-LIB benchmark (Zenodo $ZENODO_RECORD)"
    echo "=============================================="
    mkdir -p "$BENCHMARK"
    UNPACKED="$BENCHMARK/non-incremental"
    mkdir -p "$UNPACKED"

    for th in "${THEORIES[@]}"; do
        [ -z "$th" ] && continue
        # Zenodo 文件名中 _ 编码为 %5F
        name="${th//_/%5F}"
        base="${th}.tar.zst"
        url="https://zenodo.org/records/${ZENODO_RECORD}/files/${name}.tar.zst?download=1"
        dest_dir="$UNPACKED/$th"
        if [ -d "$dest_dir" ] && [ -n "$(ls -A "$dest_dir" 2>/dev/null)" ]; then
            echo "[已解压] $th -> $dest_dir"
            continue
        fi
        arc="$BENCHMARK/$base"
        echo "-------- $th --------"
        if download_url "$url" "$arc"; then
            if extract_tar_zst "$arc" "$UNPACKED"; then
                echo "[OK] $th"
            else
                echo "[解压失败] $th"
            fi
        else
            echo "[下载失败] $th ($url)"
        fi
    done
    echo ""
}

# ---------- Main ----------
echo "REPO_ROOT=$REPO_ROOT"
echo "EXTERNAL=$EXTERNAL"
echo "BENCHMARK=$BENCHMARK"
echo ""

[ "$DO_PARSERS" = 1 ]   && do_parsers
[ "$DO_BENCHMARK" = 1 ] && do_benchmark

if [ "$DO_PARSERS" = 1 ] && [ -x "$SCRIPT_DIR/build_all_parsers.sh" ]; then
    echo "=============================================="
    echo "  3. 编译所有 parsers (scripts/build_all_parsers.sh)"
    echo "=============================================="
    "$SCRIPT_DIR/build_all_parsers.sh" "$EXTERNAL" || true
fi

echo "=============================================="
echo "  完成"
echo "=============================================="
