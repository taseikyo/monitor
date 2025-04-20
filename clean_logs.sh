#!/bin/bash
# @Author: Lewis Tian
# @Date:   2025-04-20 11:40:12

# 设置保留天数
DAYS_TO_KEEP=7
echo "🧹 开始清理超过 $DAYS_TO_KEEP 天的日志文件（时间戳命名）..."

# 获取当前时间戳
current_ts=$(date +%s)
expire_ts=$((current_ts - DAYS_TO_KEEP * 86400))

# 遍历所有log目录
find . -type d -name "log" | while read log_dir; do
  echo "📂 进入目录: $log_dir"

  # 遍历所有 .log 文件
  find "$log_dir" -type f -name "*.log" | while read logfile; do
    filename=$(basename "$logfile")
    timestamp=${filename%.log}

    # 检查是否为纯数字时间戳
    if [[ $timestamp =~ ^[0-9]+$ ]]; then
      # 转换为可读时间
      human_time=$(date -d "@$timestamp" "+%Y-%m-%d %H:%M:%S")

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
