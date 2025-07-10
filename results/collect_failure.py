#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

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

def main():
    parser = argparse.ArgumentParser(description='从指定文件夹收集以"失败"结尾的行')
    parser.add_argument('directory', help='要搜索的目录路径')
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
    
    args = parser.parse_args()
    
    print("文件失败记录收集工具")
    print("=" * 50)
    
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
