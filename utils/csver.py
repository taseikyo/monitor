# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-23 18:37:57

import csv
import logging
import os
from typing import Any, List


def save_and_clean(
    filepath: str,
    logger: logging.Logger,
    header: List[str],
    data: List[Any],
    expire: int = 14,
) -> None:
    """
    将数据写入 CSV 文件，并清理指定时间前的过期数据。

    要求 `data` 的第一列为 Unix 时间戳（秒）。

    参数:
        filepath (str): CSV 文件路径。
        logger (logging.Logger): 用于记录信息和警告。
        header (List[str]): CSV 表头，必须与 data 长度一致。
        data (List[Any]): 一条待写入的数据，第一项为时间戳。
        expire (int): 数据保留的天数（默认 14 天）。
    """
    if len(header) != len(data):
        logger.warning("Header 和 data 长度不一致，写入被跳过")
        return

    timestamp = data[0]
    if not isinstance(timestamp, int):
        logger.warning("data[0] 必须为 int 类型的 Unix 时间戳")
        return

    file_exists = os.path.exists(filepath)
    existing_data: List[List[str]] = []

    # 如果文件存在，读取内容
    if file_exists:
        with open(filepath, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头
            existing_data = list(reader)

        if str(timestamp) in {row[0] for row in existing_data}:
            logger.warning(f"{timestamp} 已存在，跳过写入")
            return

    # 写入当前数据
    with open(
        filepath, mode="a" if file_exists else "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(data)
        logger.info(f"写入成功：{data}")

    # 过滤并重写未过期数据
    cutoff_time = timestamp - expire * 86400  # 86400 秒 = 1 天
    all_data = existing_data + [list(map(str, data))]
    filtered_data = [row for row in all_data if int(row[0]) >= cutoff_time]

    if len(filtered_data) < len(all_data):
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(filtered_data)
        logger.info(f"已清理 {expire} 天前的数据（时间戳 < {cutoff_time}）")
