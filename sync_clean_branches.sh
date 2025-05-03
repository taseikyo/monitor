#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-05-03 00:47:06

# 检查当前分支是否为 master
current_branch=$(git rev-parse --abbrev-ref HEAD)

if [ "$current_branch" != "master" ]; then
  echo "🔄 切换到 master 分支..."
  git checkout master
else
  echo "✅ 已经在 master 分支，无需切换。"
fi

# 同步远端状态并清理已删除的远端引用
echo "⏳ 正在同步远端并清理已删除的远端分支..."
git fetch --prune

# 查找本地分支中，远端已删除的（显示为 gone 的）
gone_branches=$(git branch -vv | awk '/: gone]/{print $1}')

if [ -z "$gone_branches" ]; then
  echo "🙌 没有需要删除的本地分支。"
else
  echo "🧹 删除以下本地分支（远端已删除）:"
  echo "$gone_branches"
  # 删除这些本地分支（已合并的），未合并的不会被删除
  echo "$gone_branches" | xargs git branch -d
  echo "✅ 已删除以上本地分支。"
fi
