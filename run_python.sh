#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-04-19 19:28:25
# @Desc：  遍历并且切换到所有子目录执行 Python 文件

echo "🌟 开始遍历子目录并执行 Python 脚本... 🌟"

# 遍历当前目录下的所有子目录
for dir in */; do
    # 检查是否是目录
    if [ -d "$dir" ]; then
        # 进入子目录
        echo "📂 进入目录: $dir"
        cd "$dir"

        # 查找当前目录下的所有.py文件并执行
        for py_file in *.py; do
            if [ -f "$py_file" ]; then
                echo "🚀 执行 $py_file..."
                if [ -f requirements.txt ]; then
                    pip3 install -r requirements.txt --break-system-packages > /dev/null
                fi
                python3 "$py_file"
                echo "✅ 执行完毕 $py_file"
                echo "------------"
            fi
        done

        # 返回上一级目录
        echo "🔙 返回上级目录"
        cd ..
    fi
done

echo "🎉 所有 Python 脚本执行完毕！🎉"
