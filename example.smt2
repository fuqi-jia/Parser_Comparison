; 简单示例：QF_LIA，用于验证各 parser 能解析并统计 AST 节点数
(set-logic QF_LIA)
(declare-fun x () Int)
(declare-fun y () Int)
(assert (> x 0))
(assert (< y 10))
(assert (= (+ x y) 15))
(check-sat)
(exit)
