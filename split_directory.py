#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹分割脚本
按照指定的文件数目将文件夹分割成多个子文件夹，保留原有的目录结构
"""

import os
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple


def count_files_recursive(directory: Path) -> int:
    """递归计算目录中的文件总数"""
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count


def get_all_files_with_structure(directory: Path) -> List[Tuple[Path, Path]]:
    """
    获取所有文件及其相对路径
    返回: [(绝对路径, 相对路径), ...]
    """
    files_list = []
    for root, dirs, files in os.walk(directory):
        root_path = Path(root)
        for file in files:
            file_path = root_path / file
            relative_path = file_path.relative_to(directory)
            files_list.append((file_path, relative_path))
    return files_list


def split_directory(input_dir: str, output_dir: str, max_files_per_split: int, copy_files: bool = True):
    """
    分割文件夹
    
    Args:
        input_dir: 输入文件夹路径
        output_dir: 输出文件夹路径
        max_files_per_split: 每个分割文件夹的最大文件数
        copy_files: True为复制文件，False为移动文件
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        raise ValueError(f"输入目录不存在: {input_dir}")
    
    if not input_path.is_dir():
        raise ValueError(f"输入路径不是目录: {input_dir}")
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 获取所有文件
    print(f"正在扫描目录: {input_dir}")
    all_files = get_all_files_with_structure(input_path)
    total_files = len(all_files)
    
    print(f"总文件数: {total_files}")
    
    if total_files == 0:
        print("目录中没有文件")
        return
    
    # 计算需要的分割数
    num_splits = (total_files + max_files_per_split - 1) // max_files_per_split
    print(f"将分割为 {num_splits} 个文件夹，每个文件夹最多 {max_files_per_split} 个文件")
    
    # 分割文件
    for split_idx in range(num_splits):
        split_name = f"part{split_idx + 1}"
        split_dir = output_path / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        
        start_idx = split_idx * max_files_per_split
        end_idx = min((split_idx + 1) * max_files_per_split, total_files)
        
        print(f"\n处理分割 {split_name} (文件 {start_idx + 1}-{end_idx}):")
        
        for i in range(start_idx, end_idx):
            src_file, relative_path = all_files[i]
            dest_file = split_dir / relative_path
            
            # 确保目标目录存在
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if copy_files:
                    shutil.copy2(src_file, dest_file)
                    action = "复制"
                else:
                    shutil.move(str(src_file), str(dest_file))
                    action = "移动"
                
                if (i - start_idx) % 100 == 0 or i == end_idx - 1:
                    print(f"  {action}了 {i - start_idx + 1}/{end_idx - start_idx} 个文件")
                    
            except Exception as e:
                print(f"  错误: 无法{action}文件 {src_file} -> {dest_file}: {e}")
    
    print(f"\n分割完成! 输出目录: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="按指定文件数目分割文件夹，保留目录结构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python split_directory.py -i /path/to/input -o /path/to/output -n 1000
  python split_directory.py -i ./benchmarks -o ./split_benchmarks -n 500 --move
        """
    )
    
    parser.add_argument('-i', '--input', required=True,
                       help='输入文件夹路径')
    parser.add_argument('-o', '--output', required=True,
                       help='输出文件夹路径')
    parser.add_argument('-n', '--max-files', type=int, required=True,
                       help='每个分割文件夹的最大文件数')
    parser.add_argument('--move', action='store_true',
                       help='移动文件而不是复制文件 (默认为复制)')
    parser.add_argument('--dry-run', action='store_true',
                       help='预览模式，只显示将要执行的操作，不实际执行')
    
    args = parser.parse_args()
    
    if args.dry_run:
        input_path = Path(args.input)
        if input_path.exists():
            total_files = count_files_recursive(input_path)
            num_splits = (total_files + args.max_files - 1) // args.max_files
            print(f"预览模式:")
            print(f"输入目录: {args.input}")
            print(f"输出目录: {args.output}")
            print(f"总文件数: {total_files}")
            print(f"每个分割最大文件数: {args.max_files}")
            print(f"将创建 {num_splits} 个分割文件夹")
            print(f"操作类型: {'移动' if args.move else '复制'}")
        else:
            print(f"错误: 输入目录不存在: {args.input}")
    else:
        try:
            split_directory(
                input_dir=args.input,
                output_dir=args.output,
                max_files_per_split=args.max_files,
                copy_files=not args.move
            )
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 