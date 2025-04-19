# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-19 18:15:47
# @Version: 3.13

import csv
import json
import logging
import os
import time
from typing import Dict

import requests


def get_today_timestamp() -> int:
    t = time.localtime()
    zero_time = time.struct_time(
        (t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, t.tm_wday, t.tm_yday, t.tm_isdst)
    )
    return int(time.mktime(zero_time))


def get_logger(
    path: str = "log", log_id: str = str(get_today_timestamp())
) -> logging.Logger:
    if not os.path.exists(path):
        os.mkdir(path)

    logger = logging.getLogger(log_id)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logfile = f"{path}/{log_id}.log"
        fh = logging.FileHandler(logfile, mode="w", encoding="utf-8")
        ch = logging.StreamHandler()

        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


def battery_info() -> Dict[str, str]:
    logger = get_logger()
    session = requests.Session()
    headers = {
        "referer": "https://www.mi.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    url = "https://api2.order.mi.com/product/view"
    payload = {"version": "2", "product_id": "13396", "t": int(time.time())}

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
    with open(
        filepath, mode="a" if file_exists else "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f)

        # 写入表头（如果是新文件）
        if not file_exists:
            writer.writerow(["timestamp", "price"])

        # 检查重复记录
        if file_exists:
            with open(filepath, mode="r", newline="", encoding="utf-8") as read_f:
                if str(current_time) in {row[0] for row in csv.reader(read_f)}:
                    logger.warning(f"{current_time} exists, skip!")
                    return

        writer.writerow([current_time, price])
        logger.info(f"time: {current_time}, price: {price}")


if __name__ == "__main__":
    query_and_save_xiaomi13()
