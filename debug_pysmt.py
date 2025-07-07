#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import json
import time
from pathlib import Path

def test_pysmt_direct():
    """直接测试pysmt解析器"""
    print("=== 直接测试pysmt解析器 ===")
    
    # 测试文件路径
    test_file = "test/counterexample.dump.ia32_Mul_base_disp--Add32.load32.Mul32.Mulh_u32.0005.smt2"
    
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        return False
    
    # 直接调用pysmt_parser.py
    parser_script = "external/pysmt/pysmt_parser.py"
    
    if not os.path.exists(parser_script):
        print(f"解析器脚本不存在: {parser_script}")
        return False
    
    print(f"运行命令: python3 {parser_script} {test_file}")
    
    try:
        result = subprocess.run(
            [sys.executable, parser_script, test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"返回码: {result.returncode}")
        print(f"标准输出:\n{result.stdout}")
        
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")
        
        # 尝试解析JSON输出
        if result.stdout.strip():
            try:
                json_result = json.loads(result.stdout)
                print(f"JSON解析成功: {json_result['success']}")
                if not json_result['success']:
                    print(f"错误信息: {json_result.get('errors', [])}")
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return False
    except Exception as e:
        print(f"执行出错: {e}")
        return False

def test_pysmt_via_cpp():
    """通过C++程序测试pysmt解析器"""
    print("\n=== 通过C++程序测试pysmt解析器 ===")
    
    # 检查是否有已编译的程序
    cpp_program = None
    possible_programs = [
        "./build/src/smt_parser_comparison",
        "./build/smt_parser_comparison",
        "./smt_parser_comparison"
    ]
    
    for prog in possible_programs:
        if os.path.exists(prog):
            cpp_program = prog
            break
    
    if not cpp_program:
        print("找不到已编译的C++程序")
        return False
    
    # 测试文件路径
    test_file = "test/counterexample.dump.ia32_Mul_base_disp--Add32.load32.Mul32.Mulh_u32.0005.smt2"
    
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        return False
    
    print(f"运行命令: {cpp_program} test --parser pysmt --file {test_file}")
    
    try:
        result = subprocess.run(
            [cpp_program, "test", "--parser", "pysmt", "--file", test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"返回码: {result.returncode}")
        print(f"标准输出:\n{result.stdout}")
        
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return False
    except Exception as e:
        print(f"执行出错: {e}")
        return False

def test_environment():
    """测试环境信息"""
    print("\n=== 环境信息 ===")
    
    print(f"Python版本: {sys.version}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python路径: {sys.executable}")
    
    # 检查pySMT是否可用
    try:
        import pysmt
        print(f"pySMT版本: {pysmt.__version__}")
        print("pySMT可用")
    except ImportError as e:
        print(f"pySMT不可用: {e}")
    
    # 检查关键文件是否存在
    key_files = [
        "external/pysmt/pysmt_parser.py",
        "test/counterexample.dump.ia32_Mul_base_disp--Add32.load32.Mul32.Mulh_u32.0005.smt2",
        "src/main.cpp",
        "build/src/smt_parser_comparison"
    ]
    
    print("\n文件检查:")
    for file_path in key_files:
        exists = os.path.exists(file_path)
        print(f"  {file_path}: {'存在' if exists else '不存在'}")

def main():
    """主函数"""
    print("SMT解析器诊断工具")
    print("=" * 50)
    
    # 测试环境
    test_environment()
    
    # 直接测试pysmt
    direct_success = test_pysmt_direct()
    
    # 通过C++程序测试
    cpp_success = test_pysmt_via_cpp()
    
    # 总结
    print("\n=== 测试总结 ===")
    print(f"直接测试pysmt: {'成功' if direct_success else '失败'}")
    print(f"通过C++程序测试: {'成功' if cpp_success else '失败'}")
    
    if direct_success and not cpp_success:
        print("\n分析: 直接测试成功但C++调用失败，可能的原因：")
        print("1. 工作目录不同")
        print("2. 环境变量差异")
        print("3. 命令行参数解析问题")
        print("4. 输入输出重定向问题")
        
        print("\n建议解决方案：")
        print("1. 重新编译项目")
        print("2. 检查C++代码中的路径处理")
        print("3. 添加更多调试信息")
    
    return direct_success and cpp_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 