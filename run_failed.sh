#!/bin/bash

# 运行失败文件的测试脚本
# 使用 build/smt_parser_wrapper 遍历运行 failed_files 中的文件
# 设置 10 秒超时，将输出重定向到文件

# 配置
PARSER_WRAPPER="build/smt_parser_wrapper"
FAILED_FILES_DIR=$1
OUTPUT_FILE="failed_files_test_output.log"
TIMEOUT_SECONDS=3

if [ -z "$1" ]; then
    FAILED_FILES_DIR="failed_files"
fi

# 创建输出文件
echo "========================================" > "$OUTPUT_FILE"
echo "失败文件测试报告" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
echo "开始时间: $(date)" >> "$OUTPUT_FILE"
echo "解析器: $PARSER_WRAPPER" >> "$OUTPUT_FILE"
echo "测试目录: $FAILED_FILES_DIR" >> "$OUTPUT_FILE"
echo "超时时间: ${TIMEOUT_SECONDS}秒" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 检查解析器是否存在
if [ ! -f "$PARSER_WRAPPER" ]; then
    echo "错误: 解析器 $PARSER_WRAPPER 不存在" | tee -a "$OUTPUT_FILE"
    exit 1
fi

# 检查失败文件目录是否存在
if [ ! -d "$FAILED_FILES_DIR" ]; then
    echo "错误: 失败文件目录 $FAILED_FILES_DIR 不存在" | tee -a "$OUTPUT_FILE"
    exit 1
fi

# 计数器
total_files=0
success_count=0
timeout_count=0
error_count=0

echo "开始处理文件..." | tee -a "$OUTPUT_FILE"
echo "----------------------------------------" >> "$OUTPUT_FILE"

# 遍历所有 .smt2 文件
while IFS= read -r -d '' file; do
    total_files=$((total_files + 1))
    
    # 获取相对路径
    relative_path=$(realpath --relative-to="$FAILED_FILES_DIR" "$file")
    
    echo "[$total_files] 处理文件: $relative_path" | tee -a "$OUTPUT_FILE"
    
    # 记录开始时间
    start_time=$(date +%s.%N)
    
    # 运行解析器，设置超时
    if timeout "$TIMEOUT_SECONDS" "$PARSER_WRAPPER" "$file" >> "$OUTPUT_FILE" 2>&1; then
        # 成功
        success_count=$((success_count + 1))
        status="✓ 成功"
    else
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            # 超时
            timeout_count=$((timeout_count + 1))
            status="⏱ 超时"
        else
            # 其他错误
            error_count=$((error_count + 1))
            status="✗ 错误 (退出码: $exit_code)"
        fi
    fi
    
    # 计算运行时间
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    
    echo "   状态: $status" >> "$OUTPUT_FILE"
    echo "   运行时间: ${runtime}秒" >> "$OUTPUT_FILE"
    echo "   文件路径: $file" >> "$OUTPUT_FILE"
    echo "----------------------------------------" >> "$OUTPUT_FILE"
    
    # 实时显示进度
    echo "   状态: $status (运行时间: ${runtime}秒)"
    
done < <(find "$FAILED_FILES_DIR" -name "*.smt2" -type f -print0)

# 生成统计报告
echo "" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
echo "测试完成统计" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
echo "结束时间: $(date)" >> "$OUTPUT_FILE"
echo "总文件数: $total_files" >> "$OUTPUT_FILE"
echo "成功数: $success_count" >> "$OUTPUT_FILE"
echo "超时数: $timeout_count" >> "$OUTPUT_FILE"
echo "错误数: $error_count" >> "$OUTPUT_FILE"
echo "成功率: $(echo "scale=2; $success_count * 100 / $total_files" | bc)%" >> "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"

# 显示最终统计
echo ""
echo "测试完成！"
echo "========================================="
echo "总文件数: $total_files"
echo "成功数: $success_count"
echo "超时数: $timeout_count"
echo "错误数: $error_count"
echo "成功率: $(echo "scale=2; $success_count * 100 / $total_files" | bc)%"
echo "========================================="
echo "详细输出已保存到: $OUTPUT_FILE"
