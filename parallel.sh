#!/bin/bash

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <parser_name>"
    echo "例如: $0 pysmt"
    exit 1
fi

PARSER=$1

# 创建结果目录
mkdir -p results/$PARSER

# 生成 part1 到 part85 的并行命令
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part1 -o results/$PARSER/part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part2 -o results/$PARSER/part2.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part3 -o results/$PARSER/part3.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part4 -o results/$PARSER/part4.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part5 -o results/$PARSER/part5.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part6 -o results/$PARSER/part6.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part7 -o results/$PARSER/part7.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part8 -o results/$PARSER/part8.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part9 -o results/$PARSER/part9.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part10 -o results/$PARSER/part10.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part11 -o results/$PARSER/part11.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part12 -o results/$PARSER/part12.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part13 -o results/$PARSER/part13.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part14 -o results/$PARSER/part14.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part15 -o results/$PARSER/part15.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part16 -o results/$PARSER/part16.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part17 -o results/$PARSER/part17.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part18 -o results/$PARSER/part18.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part19 -o results/$PARSER/part19.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part20 -o results/$PARSER/part20.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part21 -o results/$PARSER/part21.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part22 -o results/$PARSER/part22.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part23 -o results/$PARSER/part23.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part24 -o results/$PARSER/part24.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part25 -o results/$PARSER/part25.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part26 -o results/$PARSER/part26.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part27 -o results/$PARSER/part27.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part28 -o results/$PARSER/part28.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part29 -o results/$PARSER/part29.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part30 -o results/$PARSER/part30.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part31 -o results/$PARSER/part31.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part32 -o results/$PARSER/part32.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part33 -o results/$PARSER/part33.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part34 -o results/$PARSER/part34.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part35 -o results/$PARSER/part35.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part36 -o results/$PARSER/part36.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part37 -o results/$PARSER/part37.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part38 -o results/$PARSER/part38.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part39 -o results/$PARSER/part39.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part40 -o results/$PARSER/part40.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part41 -o results/$PARSER/part41.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part42 -o results/$PARSER/part42.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part43 -o results/$PARSER/part43.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part44 -o results/$PARSER/part44.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part45 -o results/$PARSER/part45.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part46 -o results/$PARSER/part46.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part47 -o results/$PARSER/part47.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part48 -o results/$PARSER/part48.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part49 -o results/$PARSER/part49.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part50 -o results/$PARSER/part50.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part51 -o results/$PARSER/part51.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part52 -o results/$PARSER/part52.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part53 -o results/$PARSER/part53.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part54 -o results/$PARSER/part54.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part55 -o results/$PARSER/part55.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part56 -o results/$PARSER/part56.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part57 -o results/$PARSER/part57.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part58 -o results/$PARSER/part58.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part59 -o results/$PARSER/part59.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part60 -o results/$PARSER/part60.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part61 -o results/$PARSER/part61.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part62 -o results/$PARSER/part62.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part63 -o results/$PARSER/part63.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part64 -o results/$PARSER/part64.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part65 -o results/$PARSER/part65.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part66 -o results/$PARSER/part66.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part67 -o results/$PARSER/part67.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part68 -o results/$PARSER/part68.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part69 -o results/$PARSER/part69.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part70 -o results/$PARSER/part70.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part71 -o results/$PARSER/part71.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part72 -o results/$PARSER/part72.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part73 -o results/$PARSER/part73.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part74 -o results/$PARSER/part74.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part75 -o results/$PARSER/part75.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part76 -o results/$PARSER/part76.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part77 -o results/$PARSER/part77.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part78 -o results/$PARSER/part78.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part79 -o results/$PARSER/part79.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part80 -o results/$PARSER/part80.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part81 -o results/$PARSER/part81.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part82 -o results/$PARSER/part82.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part83 -o results/$PARSER/part83.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part84 -o results/$PARSER/part84.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p $PARSER -d ../benchmarks/part85 -o results/$PARSER/part85.csv > /dev/null 2>/dev/null &
