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
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/small -o results/pysmt/QF_LIA_nec_smt_small.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/large/checkpass_pwd -o results/pysmt/QF_LIA_nec_smt_large_checkpass_pwd.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/large/bftpd_login -o results/pysmt/QF_LIA_nec_smt_large_bftpd_login.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/large/getoption_group -o results/pysmt/QF_LIA_nec_smt_large_getoption_group.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/large/getoption_user -o results/pysmt/QF_LIA_nec_smt_large_getoption_user.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/large/part1 -o results/pysmt/QF_LIA_nec_smt_large_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/nec-smt/med -o results/pysmt/QF_LIA_nec_smt_med.csv > /dev/null 2>/dev/null &

nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/20220307-SMPT/part1 -o results/pysmt/QF_LIA_SMPT_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/20220307-SMPT/part2 -o results/pysmt/QF_LIA_SMPT_part2.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/20220307-SMPT/part3 -o results/pysmt/QF_LIA_SMPT_part3.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_LIA/20220307-SMPT/part4 -o results/pysmt/QF_LIA_SMPT_part4.csv > /dev/null 2>/dev/null &

# 4. QF_NIA
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/part1 -o results/pysmt/QF_NIA_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/CInteger -o results/pysmt/QF_NIA_VeryMax_CInteger.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/SAT14 -o results/pysmt/QF_NIA_VeryMax_SAT14.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part1 -o results/pysmt/QF_NIA_VeryMax_ITS_part1.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part2 -o results/pysmt/QF_NIA_VeryMax_ITS_part2.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part3 -o results/pysmt/QF_NIA_VeryMax_ITS_part3.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part4 -o results/pysmt/QF_NIA_VeryMax_ITS_part4.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part5 -o results/pysmt/QF_NIA_VeryMax_ITS_part5.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part6 -o results/pysmt/QF_NIA_VeryMax_ITS_part6.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part7 -o results/pysmt/QF_NIA_VeryMax_ITS_part7.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part8 -o results/pysmt/QF_NIA_VeryMax_ITS_part8.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part9 -o results/pysmt/QF_NIA_VeryMax_ITS_part9.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part10 -o results/pysmt/QF_NIA_VeryMax_ITS_part10.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part11 -o results/pysmt/QF_NIA_VeryMax_ITS_part11.csv > /dev/null 2>/dev/null &
nohup ./build/smt_parser_comparison batch -p pysmt -d ../benchmarks/non-incremental/QF_NIA/20170427-VeryMax/ITS/part12 -o results/pysmt/QF_NIA_VeryMax_ITS_part12.csv > /dev/null 2>/dev/null &
