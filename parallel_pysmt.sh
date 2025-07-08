nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_BV/ -o results/pysmt/QF_BV.csv > pysmt.log 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_IDL/ -o results/pysmt/QF_IDL.csv > pysmt.log 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/ -o results/pysmt/QF_LIA.csv > pysmt.log 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/ -o results/pysmt/QF_NIA.csv > pysmt.log 2>/dev/null &