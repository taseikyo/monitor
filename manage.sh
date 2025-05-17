#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-05-04 13:02:12
# @Desc：  多功能Git和系统维护工具

####################### 功能函数定义 #######################

clean_logs() {
    echo "🧹 开始清理日志文件..."
    local DAYS_TO_KEEP=${1:-7}
    echo "保留天数：$DAYS_TO_KEEP 天"

    local current_ts=$(date +%s)
    local expire_ts=$((current_ts - DAYS_TO_KEEP * 86400))

    find . -type d -name "log" | while read log_dir; do
        echo "📂 进入目录: $log_dir"
        find "$log_dir" -type f -name "*.log" | while read logfile; do
            local filename=$(basename "$logfile")
            local timestamp=${filename%.log}

            if [[ $timestamp =~ ^[0-9]+$ ]]; then
                local human_time=$(date -d "@$timestamp" "+%Y-%m-%d %H:%M:%S")
                if [[ $timestamp -lt $expire_ts ]]; then
                    echo "🗑️ 删除日志: $logfile"
                    echo "   └─ 时间戳: $timestamp | $human_time"
                    rm -f "$logfile"
                fi
            else
                echo "⚠️  跳过无效文件名: $logfile"
            fi
        done
    done
    echo "🎉 日志清理完成！"
}

delete_history() {
    echo "🧹 开始清理Git历史..."
    if [ "$#" -lt 1 ]; then
        echo "❌ 必须提供至少一个路径参数！"
        exit 1
    fi

    if ! command -v git-filter-repo &> /dev/null; then
        echo "❌ 错误：未安装 git-filter-repo，请先安装它。"
        exit 1
    fi

    local REPO_URL=$(git config --get remote.origin.url)
    local REPO_NAME=$(basename -s .git "$REPO_URL")
    local MIRROR_DIR="${REPO_NAME}_mirror"

    echo "🔁 克隆裸仓库到 $MIRROR_DIR ..."
    git clone --mirror "$REPO_URL" "$MIRROR_DIR"
    cd "$MIRROR_DIR" || exit 1

    local args=()
    for path in "$@"; do
        args+=(--path "$path")
    done

    git filter-repo "${args[@]}" --invert-paths
    git push --force --mirror

    echo "✅ 以下路径已从历史中彻底删除："
    for path in "$@"; do
        echo "   - $path"
    done
}

format_python() {
    echo "🐍 开始格式化Python代码..."
    local target_dir="${1:-.}"

    if [ -f requirements.txt ]; then
        echo "😎 安装 Python 依赖..."
        pip3 install -r requirements.txt --break-system-packages > /dev/null
    fi

    local start_time=$(date +%s)
    local count=0

    mapfile -d '' py_files < <(find "$target_dir" -type f -name "*.py" -print0)
    if [ ${#py_files[@]} -eq 0 ]; then
        echo "🙅 没有找到 .py 文件。"
        return 0
    fi

    for file in "${py_files[@]}"; do
        echo "✨ 格式化：$file"
        mypy "$file"
        isort "$file"
        black "$file"
        flake8 "$file"
        count=$((count + 1))
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "✅ 共处理 $count 个文件，用时 ${duration}s 🕒"
}

sync_branches() {
    echo "🔄 开始同步Git分支..."
    local current_branch=$(git rev-parse --abbrev-ref HEAD)

    if [ "$current_branch" != "master" ]; then
        echo "🔄 切换到 master 分支..."
        git checkout master
        git pull
    else
        echo "✅ 已经在 master 分支。"
    fi

    git fetch --prune
    local gone_branches=$(git branch -vv | awk '/: gone]/{print $1}')

    if [ -z "$gone_branches" ]; then
        echo "🙌 没有需要删除的本地分支。"
    else
        echo "$gone_branches" | xargs git branch -D
        echo "✅ 已删除以下分支："
        echo "$gone_branches"
    fi

    echo "🔄 拉取 master 分支最新内容..."
    git pull
}

####################### 主逻辑 #######################

show_help() {
    echo "📌 多功能维护脚本 - 使用说明"
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "可用命令:"
    echo "  clean_logs [--days N]     清理日志文件（默认保留7天）"
    echo "  delete_history <路径...>  从Git历史删除指定路径"
    echo "  format_python [目录]      格式化Python代码（默认当前目录）"
    echo "  sync_branches            同步并清理Git分支"
    echo ""
    echo "示例:"
    echo "  $0 clean_logs --days 14"
    echo "  $0 delete_history data/ secret.txt"
    echo "  $0 format_python src/"
    echo "  $0 sync_branches"
}

case "$1" in
    clean_logs)
        shift
        DAYS=7
        while [[ "$#" -gt 0 ]]; do
            case $1 in
                --days)
                    DAYS="$2"
                    shift 2
                    ;;
                *)
                    echo "❌ 未知参数: $1"
                    exit 1
                    ;;
            esac
        done
        clean_logs "$DAYS"
        ;;
    delete_history)
        shift
        if [ "$#" -eq 0 ]; then
            echo "❌ 必须提供至少一个路径参数！"
            exit 1
        fi
        delete_history "$@"
        ;;
    format_python)
        shift
        target_dir="${1:-.}"
        format_python "$target_dir"
        ;;
    sync_branches)
        sync_branches
        ;;
    *)
        show_help
        exit 1
        ;;
esac
