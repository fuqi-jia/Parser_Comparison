nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/ -o results/pysmt/QF_BV.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_IDL/ -o results/pysmt/QF_IDL.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/ -o results/pysmt/QF_LIA.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/ -o results/pysmt/QF_NIA.csv > /dev/null 2>/dev/null &
# nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LRA/ -o results/pysmt/QF_LRA.csv > /dev/null 2>/dev/null &
# nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NRA/ -o results/pysmt/QF_NRA.csv > /dev/null 2>/dev/null &