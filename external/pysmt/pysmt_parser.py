#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import resource
import traceback
from pathlib import Path

try:
    from pysmt.smtlib.parser import SmtLibParser
    from pysmt.smtlib.script import SmtLibScript
    from pysmt.environment import get_env
    from pysmt.fnode import FNode
except ImportError as e:
    print(json.dumps({
        "success": False,
        "parse_time": 0,
        "memory_usage": 0,
        "ast_node_count": 0,
        "errors": [f"pySMT未安装或导入失败: {str(e)}"]
    }))
    sys.exit(1)

def count_nodes(node):
    """递归计算AST节点数"""
    if not isinstance(node, FNode):
        return 1
    
    count = 1
    if hasattr(node, 'args') and node.args:
        for arg in node.args:
            count += count_nodes(arg)
    return count

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
        # 检查文件是否存在
        if not Path(filename).exists():
            result["errors"].append(f"文件不存在: {filename}")
            return result
        
        # 记录开始时间和内存
        start_time = time.time()
        start_memory = get_memory_usage()
        
        # 创建解析器
        parser = SmtLibParser()
        
        # 解析文件
        script = parser.get_script_fname(filename)
        
        # 计算解析时间
        end_time = time.time()
        parse_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        # 计算内存使用
        end_memory = get_memory_usage()
        memory_usage = max(0, end_memory - start_memory)
        
        # 计算AST节点数
        ast_node_count = 0
        if hasattr(script, 'commands') and script.commands:
            ast_node_count = len(script.commands)
            
            # 如果可以访问到具体的表达式，计算更详细的节点数
            try:
                for cmd in script.commands:
                    if hasattr(cmd, 'args') and cmd.args:
                        for arg in cmd.args:
                            if isinstance(arg, FNode):
                                ast_node_count += count_nodes(arg)
            except:
                # 如果详细计算失败，使用命令数量作为节点数
                pass
        
        # 填充结果
        result["success"] = True
        result["parse_time"] = parse_time
        result["memory_usage"] = memory_usage
        result["ast_node_count"] = ast_node_count
        
    except Exception as e:
        result["success"] = False
        result["errors"].append(f"解析错误: {str(e)}")
        # 如果有详细的错误信息，也添加进去
        if hasattr(e, '__traceback__'):
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            result["errors"].append(f"详细错误: {tb_str}")
    
    return result

def main():
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "parse_time": 0,
            "memory_usage": 0,
            "ast_node_count": 0,
            "errors": ["用法: python pysmt_parser.py <smt_file>"]
        }))
        sys.exit(1)
    
    filename = sys.argv[1]
    result = parse_smt_file(filename)
    
    # 输出JSON结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
