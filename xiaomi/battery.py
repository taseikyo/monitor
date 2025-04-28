# -*- coding: utf-8 -*-
# @Author:  Lewis Tian
# @Date:    2025-04-19 18:15:47
# @Version: 3.13
# @Desc:    监控小米13电池服务价格变化

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
from utils.csver import save_and_clean  # noqa: E402
from utils.filer import update_readme_with_table  # noqa: E402
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
        logger.info(f"Response Text: {response.text}")
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
    logger = get_logger()
    binfo = battery_info()
    key = "Xiaomi 13 电池换新服务"
    price = binfo.get(key, "-1")
    if price != "-1":
        logger.info(f"✅ 今日 Xiaomi 13 电池换新服务价格：{price}")
    else:
        logger.warning("⚠️ 获取失败")
        return

    current_directory = os.path.dirname(__file__)
    csv_dir = os.path.join(current_directory, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    filepath = os.path.join(csv_dir, "xiaomi13.csv")
    save_and_clean(
        filepath, logger, ["timestamp", "price"], [get_today_timestamp(), price], 7
    )

    parent_directory = os.path.dirname(current_directory)
    update_readme_with_table(
        logger, filepath, f"{parent_directory}/README.md", "xiaomi13battery"
    )


if __name__ == "__main__":
    query_and_save_xiaomi13()
