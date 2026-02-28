#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import resource
import traceback
import os
from pathlib import Path

try:
    from pysmt.smtlib.parser import SmtLibParser
    from pysmt.environment import get_env
except ImportError as e:
    print(json.dumps({
        "success": False,
        "parse_time": 0,
        "memory_usage": 0,
        "ast_node_count": 0,
        "errors": [f"pySMT未安装或导入失败: {str(e)}"]
    }), file=sys.stderr)
    sys.exit(1)

def get_memory_usage():
    """获取当前内存使用量(KB)"""
    try:
        # Linux下使用资源统计
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss在Linux下是KB，在macOS下是bytes
        if sys.platform == 'darwin':
            return usage.ru_maxrss // 1024
        else:
            return usage.ru_maxrss
    except:
        return 0


def count_formula_nodes(formula):
    """迭代计算公式的唯一节点数（避免重复子树）"""
    if formula is None:
        return 0

    visited = set()
    stack = [formula]
    count = 0

    while stack:
        node = stack.pop()
        if node is None:
            continue

        node_id = node.node_id()
        if node_id in visited:
            continue  # 已访问过，避免重复计数

        visited.add(node_id)
        count += 1  # 当前节点本身

        # 将子节点加入栈中
        try:
            for arg in node.args():
                stack.append(arg)
        except Exception:
            # 某些节点可能不支持 args()，忽略即可
            pass

    return count


def parse_smt_file(filename):
    """解析SMT文件并返回结果"""
    result = {
        "success": False,
        "parse_time": 0,
        "memory_usage": 0,
        "ast_node_count": 0,
        "errors": []
    }
    
    try:
        # 添加调试信息
        debug_info = {
            "cwd": os.getcwd(),
            "file_path": os.path.abspath(filename),
            "file_exists": os.path.exists(filename),
            "python_version": sys.version,
            "argv": sys.argv
        }
        
        # 检查文件是否存在
        if not Path(filename).exists():
            result["errors"].append(f"文件不存在: {filename}")
            result["errors"].append(f"调试信息: {debug_info}")
            return result
        
        # 记录开始时间和内存
        start_time = time.time()
        start_memory = get_memory_usage()
        
        # 创建解析器和环境
        parser = SmtLibParser()
        
        # 解析文件
        try:
            script = parser.get_script_fname(filename)
        except Exception as parse_error:
            result["errors"].append(f"解析文件失败: {str(parse_error)}")
            result["errors"].append(f"错误类型: {type(parse_error).__name__}")
            result["errors"].append(f"调试信息: {debug_info}")
            # 添加详细的错误跟踪
            tb_str = ''.join(traceback.format_exc())
            result["errors"].append(f"详细错误跟踪: {tb_str}")
            return result
        
        # 计算解析时间
        end_time = time.time()
        parse_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        # 计算内存使用：与其它 parser 一致，上报进程峰值 RSS (ru_maxrss)，而非增量
        end_memory = get_memory_usage()
        memory_usage = end_memory
        
        # 计算AST节点数
        ast_node_count = 0
        
        try:
            # 计算命令数量
            if hasattr(script, 'commands') and script.commands:
                ast_node_count = len(script.commands)
                
                # 尝试获取更详细的节点数（通过get_last_formula）
                try:
                    last_formula = script.get_last_formula()
                    if last_formula is not None:
                        # 使用公式的节点计数
                        formula_nodes = count_formula_nodes(last_formula)
                        ast_node_count = max(ast_node_count, formula_nodes)
                except Exception as formula_error:
                    # 如果获取公式失败，使用命令数量
                    result["errors"].append(f"获取公式失败: {str(formula_error)}")
            elif hasattr(script, 'commands'):
                # commands存在但为空
                ast_node_count = 0
            else:
                # 无法访问commands，估算为1
                ast_node_count = 1
                
        except Exception as count_error:
            # 如果计算节点数失败，使用默认值
            ast_node_count = 1
            result["errors"].append(f"计算节点数失败: {str(count_error)}")
            
        # 填充结果
        result["success"] = True
        result["parse_time"] = parse_time
        result["memory_usage"] = memory_usage
        result["ast_node_count"] = ast_node_count
        
    except Exception as e:
        result["success"] = False
        result["errors"].append(f"解析错误: {str(e)}")
        result["errors"].append(f"错误类型: {type(e).__name__}")
        # 添加详细的错误信息
        tb_str = ''.join(traceback.format_exc())
        result["errors"].append(f"详细错误跟踪: {tb_str}")
        
        # 添加调试信息
        debug_info = {
            "cwd": os.getcwd(),
            "file_path": os.path.abspath(filename) if filename else "None",
            "file_exists": os.path.exists(filename) if filename else False,
            "python_version": sys.version,
            "argv": sys.argv
        }
        result["errors"].append(f"调试信息: {debug_info}")
    
    return result

def main():
    if len(sys.argv) != 2:
        error_result = {
            "success": False,
            "parse_time": 0,
            "memory_usage": 0,
            "ast_node_count": 0,
            "errors": [f"用法: python pysmt_parser.py <smt_file>", f"接收到的参数: {sys.argv}"]
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    filename = sys.argv[1]
    result = parse_smt_file(filename)
    
    # 输出JSON结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
