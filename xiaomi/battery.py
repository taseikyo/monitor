# -*- coding: utf-8 -*-
# @Author:  Lewis Tian
# @Date:    2025-04-19 18:15:47
# @Version: 3.13
# @Desc:    监控小米13电池服务价格变化

import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict
from zoneinfo import ZoneInfo

import requests

# 添加项目根目录到 sys.path，确保能导入 bootstrap.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from utils.logger import get_logger  # noqa: E402
from utils.timer import get_today_timestamp  # noqa: E402


def battery_info() -> Dict[str, str]:
    logger = get_logger()
    session = requests.Session()
    headers = {
        "referer": "https://www.mi.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    url = "https://api2.order.mi.com/product/view"
    payload = {
        "version": "2",
        "product_id": "13396",
        "t": str(int(datetime.now(ZoneInfo("Asia/Shanghai")).timestamp())),
    }

    try:
        response = session.get(url, params=payload, headers=headers, timeout=10)
        logger.info(f"Request URL: {response.url}")
        logger.info(
            f"Response Text: {response.text.replace(' ', '').replace('\n', '')}"
        )
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {}

    try:
        resp = response.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return {}

    if not resp:
        logger.warning("Empty response.")
        return {}

    data = resp.get("data", {})
    goods_list = data.get("goods_list", [])

    result = {}
    for goods in goods_list:
        info = goods.get("goods_info", {})
        name = info.get("name", "")
        price = info.get("price", "")
        if name:
            result[name] = price

    return result


def query_and_save_xiaomi13():
    if not os.path.exists("csv"):
        os.mkdir("csv")

    current_time = get_today_timestamp()
    binfo = battery_info()
    key = "Xiaomi 13 电池换新服务"
    price = binfo.get(key, "未找到")
    logger = get_logger()

    filepath = "csv/xiaomi13.csv"
    file_exists = os.path.exists(filepath)

    # 读取现有数据（如果存在）
    existing_data = []
    if file_exists:
        with open(filepath, mode="r", newline="", encoding="utf-8") as read_f:
            reader = csv.reader(read_f)
            next(reader, None)
            existing_data = list(reader)
            if str(current_time) in {row[0] for row in existing_data}:
                logger.warning(f"{current_time} exists, skip!")
                return

    # 写入新数据
    with open(
        filepath, mode="a" if file_exists else "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "price"])
        writer.writerow([current_time, price])
        logger.info(f"写入成功：time: {current_time}, price: {price}")

    # 清理14天前的数据
    fourteen_days_ago = current_time - 14 * 24 * 3600
    all_data = existing_data + [[str(current_time), price]]
    filtered_data = [row for row in all_data if int(row[0]) >= fourteen_days_ago]

    # 如有变动则重写文件
    if len(filtered_data) < len(all_data):
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "price"])
            writer.writerows(filtered_data)
        logger.info("已清理14天前的数据")


if __name__ == "__main__":
    query_and_save_xiaomi13()
