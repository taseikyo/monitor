#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-05-04 11:15:35


# 检查依赖
if ! command -v git-filter-repo &> /dev/null
then
    echo "❌ 错误：未安装 git-filter-repo，请先安装它。"
    exit 1
fi

# 检查参数
if [ "$#" -lt 1 ]; then
    echo "📌 用法: $0 <path1> [<path2> ...]"
    echo "   示例: $0 data/large_folder secret.txt"
    exit 1
fi

# 克隆当前仓库为裸仓库
REPO_URL=$(git config --get remote.origin.url)
REPO_NAME=$(basename -s .git "$REPO_URL")
MIRROR_DIR="${REPO_NAME}_mirror"

echo "🔁 克隆裸仓库到 $MIRROR_DIR ..."
git clone --mirror "$REPO_URL" "$MIRROR_DIR"

cd "$MIRROR_DIR" || exit 1

# 构建 --path 参数
ARGS=()
for path in "$@"; do
    ARGS+=(--path "$path")
done

# 删除指定路径
echo "🧹 正在删除以下路径（包括历史记录）..."
for path in "$@"; do
    echo "   - $path"
done
git filter-repo "${ARGS[@]}" --invert-paths

# 强制推送
echo "🚀 推送修改到远程仓库（⚠️ 这会覆盖历史）..."
git push --force --mirror

# 完成提示
echo "✅ 操作完成！以下路径已从历史中彻底删除："
for path in "$@"; do
    echo "   - $path"
done
