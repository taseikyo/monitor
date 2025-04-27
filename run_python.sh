#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-04-19 19:28:25
# @Desc：  遍历并且切换到所有子目录执行 Python 文件，使用并行处理每个子目录，并记录每个子目录运行耗时

echo "🌟 开始遍历子目录并执行 Python 脚本... 🌟"

# 定义一个函数，用来处理每个子目录中的 Python 脚本执行
process_directory() {
    local dir="$1"
    local start_time=$(date +%s)  # 记录开始时间
    echo "📂 进入目录: $dir"
    cd "$dir" || return 1

    if [ -f requirements.txt ]; then
        echo "😎 安装 Python 依赖..."
        pip3 install -r requirements.txt --break-system-packages > /dev/null
    fi

    # 查找当前目录下的所有 .py 文件并执行
    for py_file in *.py; do
        if [ -f "$py_file" ]; then
            echo "🚀 执行 $py_file..."
            python3 "$py_file"
            echo "✅ 执行完毕 $py_file"
            echo "------------"
        fi
    done

    # 返回上一级目录
    echo "🔙 返回上级目录"
    cd .. || return 1

    local end_time=$(date +%s)  # 记录结束时间
    local elapsed_time=$((end_time - start_time))  # 计算耗时
    echo "⏱️ 目录 $dir 执行完毕，耗时: $elapsed_time 秒"
}

# 遍历当前目录下的所有子目录并行执行
for dir in */; do
    # 检查是否是目录
    if [ -d "$dir" ]; then
        # 启动后台进程执行子目录中的操作
        process_directory "$dir" &
    fi
done

# 等待所有后台进程完成
wait

echo "🎉 所有 Python 脚本执行完毕！🎉"
