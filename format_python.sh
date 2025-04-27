#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-04-19 18:44:47
# @Desc：  使用 black 和 isort 格式化

format_py() {
    target_dir="${1:-.}"

    echo "🐍 Python 自动格式化工具"

    if [ -f requirements.txt ]; then
        echo "😎 安装 Python 依赖..."
        pip3 install -r requirements.txt --break-system-packages > /dev/null
    fi

    echo "📂 目标目录：$target_dir"
    echo "🔍 正在查找 Python 文件..."

    start_time=$(date +%s)
    count=0

    # 使用 find 查找所有 .py 文件
    mapfile -d '' py_files < <(find "$target_dir" -type f -name "*.py" -print0)

    if [ ${#py_files[@]} -eq 0 ]; then
        echo "🙅 没有找到 .py 文件，无需格式化。"
        return 0
    fi

    echo "🎯 开始格式化 ${#py_files[@]} 个 Python 文件..."

    for file in "${py_files[@]}"; do
        echo "✨ 格式化：$file"
        echo "  ✨ mypy：$file"
        mypy "$file"
        echo "  ✨ isort：$file"
        isort "$file"
        echo "  ✨ black：$file"
        black "$file"
        echo "  ✨ flake8：$file"
        flake8 "$file"
        echo "✅ 执行完毕 $file"
        echo "------------"
        count=$((count + 1))
    done

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo "✅ 全部格式化完成！"
    echo "📊 共处理 $count 个文件，用时 ${duration}s 🕒"
}

# 如果是脚本被直接执行，则调用函数并传递参数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    format_py "$@"
fi
