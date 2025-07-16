#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import shutil
import re

def collect_failure_lines(directory, output_file="failure_report.txt", file_extensions=None):
    """
    从指定目录收集以"失败"结尾的行，生成记录文件
    
    Args:
        directory: 要搜索的目录路径
        output_file: 输出文件名
        file_extensions: 要搜索的文件扩展名列表，如 ['.txt', '.log']
    """
    
    if file_extensions is None:
        file_extensions = ['.txt', '.log', '.out', '.err', '.result', '.csv']
    
    directory = Path(directory)
    if not directory.exists():
        print(f"错误: 目录 '{directory}' 不存在")
        return False
    
    failure_records = []
    processed_files = 0
    total_lines = 0
    failure_count = 0
    
    print(f"开始扫描目录: {directory}")
    print(f"搜索文件类型: {file_extensions}")
    print("-" * 50)
    
    # 遍历目录中的所有文件
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            # 检查文件扩展名
            if file_extensions and file_path.suffix.lower() not in file_extensions:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    processed_files += 1
                    
                    for line_num, line in enumerate(lines, 1):
                        total_lines += 1
                        line = line.strip()
                        
                        # 检查行末尾是否为"失败"
                        if line.endswith("失败"):
                            failure_count += 1
                            failure_records.append({
                                'file': str(file_path.relative_to(directory)),
                                'line_number': line_num,
                                'content': line,
                                'full_path': str(file_path)
                            })
                            print(f"发现失败: {file_path.name}:{line_num} - {line[:50]}...")
                            
            except Exception as e:
                print(f"警告: 读取文件 {file_path} 时出错: {e}")
                continue
    
    # 生成报告文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入报告头部
            f.write("=" * 60 + "\n")
            f.write("失败记录收集报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"扫描目录: {directory}\n")
            f.write(f"处理文件数: {processed_files}\n")
            f.write(f"总行数: {total_lines}\n")
            f.write(f"失败记录数: {failure_count}\n")
            f.write("=" * 60 + "\n\n")
            
            if failure_records:
                f.write("失败记录详情:\n")
                f.write("-" * 60 + "\n")
                
                for i, record in enumerate(failure_records, 1):
                    f.write(f"[{i:03d}] 文件: {record['file']}\n")
                    f.write(f"      行号: {record['line_number']}\n")
                    f.write(f"      内容: {record['content']}\n")
                    f.write(f"      路径: {record['full_path']}\n")
                    f.write("-" * 60 + "\n")
                
                # 按文件分组统计
                f.write("\n按文件统计:\n")
                f.write("-" * 60 + "\n")
                file_stats = {}
                for record in failure_records:
                    file_name = record['file']
                    if file_name not in file_stats:
                        file_stats[file_name] = 0
                    file_stats[file_name] += 1
                
                for file_name, count in sorted(file_stats.items()):
                    f.write(f"{file_name}: {count} 个失败\n")
                
            else:
                f.write("未发现以'失败'结尾的行。\n")
            
            f.write(f"\n报告生成完成。\n")
        
        print(f"\n报告已生成: {output_file}")
        print(f"共发现 {failure_count} 个失败记录")
        return True
        
    except Exception as e:
        print(f"错误: 生成报告文件时出错: {e}")
        return False

def collect_failure_patterns(directory, output_file="failure_patterns.txt", patterns=None):
    """
    收集包含失败模式的行（更灵活的搜索）
    
    Args:
        directory: 要搜索的目录路径
        output_file: 输出文件名
        patterns: 失败模式列表，如 ['失败', 'FAILED', 'ERROR', 'FAIL']
    """
    
    if patterns is None:
        patterns = ['失败', 'FAILED', 'ERROR', 'FAIL', '错误', 'EXCEPTION']
    
    directory = Path(directory)
    if not directory.exists():
        print(f"错误: 目录 '{directory}' 不存在")
        return False
    
    failure_records = []
    processed_files = 0
    total_lines = 0
    
    print(f"开始扫描目录: {directory}")
    print(f"搜索模式: {patterns}")
    print("-" * 50)
    
    # 遍历目录中的所有文件
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.log', '.out', '.err', '.result']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    processed_files += 1
                    
                    for line_num, line in enumerate(lines, 1):
                        total_lines += 1
                        line_content = line.strip()
                        
                        # 检查是否包含任何失败模式
                        for pattern in patterns:
                            if pattern in line_content:
                                failure_records.append({
                                    'file': str(file_path.relative_to(directory)),
                                    'line_number': line_num,
                                    'content': line_content,
                                    'pattern': pattern,
                                    'full_path': str(file_path)
                                })
                                print(f"发现模式 '{pattern}': {file_path.name}:{line_num}")
                                break  # 避免同一行被多个模式匹配
                            
            except Exception as e:
                print(f"警告: 读取文件 {file_path} 时出错: {e}")
                continue
    
    # 生成报告
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("失败模式收集报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"扫描目录: {directory}\n")
            f.write(f"搜索模式: {', '.join(patterns)}\n")
            f.write(f"处理文件数: {processed_files}\n")
            f.write(f"失败记录数: {len(failure_records)}\n")
            f.write("=" * 60 + "\n\n")
            
            if failure_records:
                f.write("失败记录详情:\n")
                f.write("-" * 60 + "\n")
                
                for i, record in enumerate(failure_records, 1):
                    f.write(f"[{i:03d}] 文件: {record['file']}\n")
                    f.write(f"      行号: {record['line_number']}\n")
                    f.write(f"      模式: {record['pattern']}\n")
                    f.write(f"      内容: {record['content']}\n")
                    f.write("-" * 60 + "\n")
                
                # 按模式统计
                f.write("\n按模式统计:\n")
                f.write("-" * 60 + "\n")
                pattern_stats = {}
                for record in failure_records:
                    pattern = record['pattern']
                    if pattern not in pattern_stats:
                        pattern_stats[pattern] = 0
                    pattern_stats[pattern] += 1
                
                for pattern, count in sorted(pattern_stats.items()):
                    f.write(f"{pattern}: {count} 次\n")
            else:
                f.write("未发现匹配的失败模式。\n")
        
        print(f"\n模式报告已生成: {output_file}")
        return True
        
    except Exception as e:
        print(f"错误: 生成报告文件时出错: {e}")
        return False

server_path = "../benchmarks/benchmarks"

def copy_failed_files_from_log(log_file, target_dir, base_source_dir=None):
    """
    从native_error.log中提取失败文件并复制到指定目录
    
    Args:
        log_file: native_error.log文件路径
        target_dir: 目标目录路径
        base_source_dir: 基础源目录路径（用于构建实际文件路径）
    """
    
    log_file = Path(log_file)
    target_dir = Path(target_dir)
    
    if not log_file.exists():
        print(f"错误: 日志文件 '{log_file}' 不存在")
        return False
    
    # 创建目标目录
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"目标目录: {target_dir}")
    
    # 如果没有指定基础源目录，尝试自动推断
    if base_source_dir is None:
        base_source_dir = Path.cwd()
    else:
        base_source_dir = Path(base_source_dir)
    
    failed_files = []
    copied_files = 0
    missing_files = 0
    
    print(f"开始解析日志文件: {log_file}")
    print("-" * 60)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # 查找包含文件路径的行
                if line.startswith("内容: ") and line.endswith("失败"):
                    # 提取文件路径（逗号前的部分）
                    content = line[4:]  # 去掉"内容: "前缀
                    file_path = content.split(',')[0]  # 取第一个逗号前的部分
                    
                    # 转换路径格式
                    # 从: /pub/data/jiafq/iscas/Parser_Comparison/../benchmarks/part8/non-incremental/QF_BV/mcm/186.smt2
                    # 到: ../../benchmarks/benchmarks/part8/non-incremental/QF_BV/mcm/186.smt2
                    
                    # 查找benchmarks部分
                    if '../benchmarks/' in file_path:
                        # 提取benchmarks之后的路径
                        benchmark_part = file_path.split('../benchmarks/')[-1]
                        new_path = f"{server_path}/{benchmark_part}"
                        
                        failed_files.append({
                            'original_path': file_path,
                            'new_path': new_path,
                            'line_number': line_num,
                            'content': line
                        })
                        
                        print(f"发现失败文件: {benchmark_part}")
    
    except Exception as e:
        print(f"错误: 解析日志文件时出错: {e}")
        return False
    
    print(f"\n共发现 {len(failed_files)} 个失败文件")
    print("-" * 60)
    
    # 复制文件
    for i, file_info in enumerate(failed_files, 1):
        original_path = file_info['original_path']
        new_path = file_info['new_path']
        
        # 构建实际源文件路径
        source_file = new_path
        
        # 构建目标文件路径
        target_file = target_dir 
        
        try:
            if os.path.exists(source_file):
                # 创建目标文件的父目录
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                shutil.copy2(source_file, target_file)
                copied_files += 1
                print(f"[{i:03d}] ✓ 复制成功: {source_file} to {target_file}")
            else:
                missing_files += 1
                print(f"[{i:03d}] ✗ 文件不存在: {source_file}")
                
        except Exception as e:
            print(f"[{i:03d}] ✗ 复制失败: {source_file} - {e}")
            continue
    
    # 生成复制报告
    report_file = target_dir / "copy_report.txt"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("失败文件复制报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"源日志文件: {log_file}\n")
            f.write(f"目标目录: {target_dir}\n")
            f.write(f"基础源目录: {base_source_dir}\n")
            f.write(f"发现失败文件数: {len(failed_files)}\n")
            f.write(f"成功复制文件数: {copied_files}\n")
            f.write(f"缺失文件数: {missing_files}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("复制详情:\n")
            f.write("-" * 60 + "\n")
            
            for i, file_info in enumerate(failed_files, 1):
                f.write(f"[{i:03d}] 原始路径: {file_info['original_path']}\n")
                f.write(f"      新路径: {file_info['new_path']}\n")
                f.write(f"      日志行号: {file_info['line_number']}\n")
                
                # 检查是否复制成功
                target_file = target_dir / file_info['new_path']
                if target_file.exists():
                    f.write(f"      状态: ✓ 复制成功\n")
                else:
                    f.write(f"      状态: ✗ 复制失败\n")
                f.write("-" * 60 + "\n")
            
            f.write(f"\n报告生成完成。\n")
        
        print(f"\n复制报告已生成: {report_file}")
        
    except Exception as e:
        print(f"警告: 生成复制报告时出错: {e}")
    
    print(f"\n复制完成统计:")
    print(f"  总失败文件数: {len(failed_files)}")
    print(f"  成功复制: {copied_files}")
    print(f"  缺失文件: {missing_files}")
    print(f"  目标目录: {target_dir}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='从指定文件夹收集以"失败"结尾的行')
    parser.add_argument('directory', nargs='?', help='要搜索的目录路径')
    parser.add_argument('-o', '--output', default='failure_report.txt', 
                       help='输出文件名 (默认: failure_report.txt)')
    parser.add_argument('-e', '--extensions', nargs='*', 
                       default=['.txt', '.log', '.out', '.err', '.result', '.csv'],
                       help='要搜索的文件扩展名 (默认: .txt .log .out .err .result)')
    parser.add_argument('-p', '--pattern-mode', action='store_true',
                       help='使用模式匹配模式（搜索失败、ERROR等关键词）')
    parser.add_argument('--patterns', nargs='*',
                       default=['失败', 'FAILED', 'ERROR', 'FAIL', '错误', 'EXCEPTION'],
                       help='在模式模式下要搜索的模式列表')
    parser.add_argument('--copy-from-log', help='从指定的日志文件复制失败文件')
    parser.add_argument('--target-dir', default='failed_files', 
                       help='复制文件的目标目录 (默认: failed_files)')
    parser.add_argument('--source-base', help='基础源目录路径')
    
    args = parser.parse_args()
    
    print("文件失败记录收集工具")
    print("=" * 50)
    
    # 如果指定了从日志文件复制
    if args.copy_from_log:
        success = copy_failed_files_from_log(
            args.copy_from_log, 
            args.target_dir, 
            args.source_base
        )
        if success:
            print("\n✓ 文件复制完成")
        else:
            print("\n✗ 文件复制失败")
            sys.exit(1)
        return
    
    # 如果没有提供目录参数，退出
    if not args.directory:
        print("错误: 必须提供目录路径或使用 --copy-from-log 参数")
        sys.exit(1)
    
    if args.pattern_mode:
        success = collect_failure_patterns(
            args.directory, 
            args.output, 
            args.patterns
        )
    else:
        success = collect_failure_lines(
            args.directory, 
            args.output, 
            args.extensions
        )
    
    if success:
        print("\n✓ 收集完成")
    else:
        print("\n✗ 收集失败")
        sys.exit(1)

if __name__ == "__main__":
    # 如果没有命令行参数，提供交互式使用
    if len(sys.argv) == 1:
        print("文件失败记录收集工具")
        print("=" * 50)
        
        print("选择功能:")
        print("1. 从目录收集失败记录")
        print("2. 从日志文件复制失败文件")
        
        choice = input("请选择 (1 或 2): ").strip()
        
        if choice == "2":
            log_file = input("请输入日志文件路径 (如: native_error.log): ").strip()
            if not log_file:
                print("错误: 必须提供日志文件路径")
                sys.exit(1)
            
            target_dir = input("请输入目标目录 (默认: failed_files): ").strip()
            if not target_dir:
                target_dir = "failed_files"
            
            source_base = input("请输入基础源目录路径 (默认: 当前目录): ").strip()
            if not source_base:
                source_base = None
            
            success = copy_failed_files_from_log(log_file, target_dir, source_base)
            
            if success:
                print(f"\n✓ 文件复制完成，目标目录: {target_dir}")
            else:
                print("\n✗ 文件复制失败")
                sys.exit(1)
        
        else:
            directory = input("请输入要搜索的目录路径: ").strip()
            if not directory:
                print("错误: 必须提供目录路径")
                sys.exit(1)
            
            output_file = input("请输入输出文件名 (默认: failure_report.txt): ").strip()
            if not output_file:
                output_file = "failure_report.txt"
            
            mode = input("选择模式 [1] 精确匹配（以'失败'结尾） [2] 模式匹配（包含失败关键词） (默认: 1): ").strip()
            
            if mode == "2":
                patterns = input("请输入搜索模式，用空格分隔 (默认: 失败 ERROR FAIL): ").strip()
                if patterns:
                    pattern_list = patterns.split()
                else:
                    pattern_list = ['失败', 'ERROR', 'FAIL']
                
                success = collect_failure_patterns(directory, output_file, pattern_list)
            else:
                extensions = input("请输入文件扩展名，用空格分隔 (默认: .txt .log .out): ").strip()
                if extensions:
                    ext_list = [ext if ext.startswith('.') else '.' + ext for ext in extensions.split()]
                else:
                    ext_list = ['.txt', '.log', '.out', '.err', '.result']
                
                success = collect_failure_lines(directory, output_file, ext_list)
            
            if success:
                print(f"\n✓ 收集完成，报告已保存到: {output_file}")
            else:
                print("\n✗ 收集失败")
                sys.exit(1)
    else:
        main()
