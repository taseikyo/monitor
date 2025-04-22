# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-22 22:46:31
# @Desc:   自动签到领京豆
# @Ref:    https://github.com/nibabashilkk/alipan_auto_sign

import argparse
import json
import os
import sys

import requests

# 添加项目根目录到 sys.path，确保能导入 bootstrap.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from utils.logger import get_logger  # noqa: E402


def get_bean(cookie: str = "") -> int:
    logger = get_logger()
    session = requests.Session()
    url = "https://api.m.jd.com/client.action?functionId=signBeanAct&appid=ld&client=apple"  # noqa: E501
    if not cookie:
        logger.error("empty cookie")
        return -1

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "cookie": cookie,
    }
    try:
        response = session.post(url, headers=headers, timeout=10)
        logger.info(f"Request URL: {response.url}")
        logger.info(
            f"Response Text: {response.text.replace(' ', '').replace('\n', '')}"
        )
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return -1

    try:
        resp = response.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return -1

    if not resp:
        logger.warning("Empty response.")
        return -1

    data = resp.get("data", {})

    dailyAward = data.get("dailyAward", {})
    if not dailyAward:
        dailyAward = data.get("continuityAward", {})
    if not dailyAward:
        dailyAward = data.get("newUserAward", {})
    if not dailyAward:
        logger.error("Fail to get 'dailyAward' data")
        return -1
    beanAward = dailyAward.get("beanAward", {})
    beanCount = beanAward.get("beanCount", -1)

    return beanCount


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动签到领京豆")
    parser.add_argument("--cookie", required=False, help="JD Cookie，用于身份认证")
    args = parser.parse_args()

    cookie = args.cookie or os.getenv("JD_COOKIE")
    if not cookie:
        cookie = ""
    count = get_bean(cookie=cookie)
    logger = get_logger()
    logger.info(f"今天获得京豆：{count}")
