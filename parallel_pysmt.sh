# 1. QF_LRA + QF_NRA + QF_BV
# nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LRA/ -o results/pysmt/QF_LRA.csv > /dev/null 2>/dev/null &
# nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NRA/ -o results/pysmt/QF_NRA.csv > /dev/null 2>/dev/null &
# nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/Sage2 -o results/pysmt/QF_BV_Sage2.csv > /dev/null 2>/dev/null &
# nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/part1 -o results/pysmt/QF_BV_part1.csv > /dev/null 2>/dev/null &

# 2. QF_BV
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/part2 -o results/pysmt/QF_BV_part2.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/sage/part1 -o results/pysmt/QF_BV_sage_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/sage/part2 -o results/pysmt/QF_BV_sage_part2.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/sage/app7 -o results/pysmt/QF_BV_sage_app7.csv > /dev/null 2>/dev/null &

# 3. QF_IDL + QF_LIA + QF_NIA
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_IDL/ -o results/pysmt/QF_IDL.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/part1 -o results/pysmt/QF_LIA_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/20220307-SMPT -o results/pysmt/QF_LIA_SMPT.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/part1 -o results/pysmt/QF_NIA_part1.csv > /dev/null 2>/dev/null &

# 4. QF_NIA
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/part1 -o results/pysmt/QF_NIA_VeryMax_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part1 -o results/pysmt/QF_NIA_VeryMax_ITS_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part2 -o results/pysmt/QF_NIA_VeryMax_ITS_part2.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part3 -o results/pysmt/QF_NIA_VeryMax_ITS_part3.csv > /dev/null 2>/dev/null &
