# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-23 19:45:02

import argparse
import json
import os
import sys
from logging import Logger

import requests

# 添加项目根目录到 sys.path，确保能导入 bootstrap.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from model.ctrip_sign import CtripSignResponse  # noqa: E402
from utils.csver import save_and_clean  # noqa: E402
from utils.filer import update_readme_with_table  # noqa: E402
from utils.logger import get_logger  # noqa: E402
from utils.timer import get_today_timestamp  # noqa: E402


def sign(logger: Logger, cookie: str = "") -> int:
    session = requests.Session()
    url = "https://m.ctrip.com/restapi/soa2/22769/signToday"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "cookie": cookie,
    }
    try:
        response = session.get(url, headers=headers, timeout=10)
        logger.info(f"Request URL: {response.url}")
        resp = response.json()
    except requests.RequestException as e:
        logger.info(
            f"Response Text: {response.text.replace(' ', '').replace('\n', '')}"
        )
        logger.error(f"Request failed: {e}")
        return -1
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return -1

    if not resp:
        logger.warning("Empty response.")
        return -1

    csResp = CtripSignResponse.model_validate(resp)
    if csResp.code == 400001:
        logger.info("今日已签到")
        return -1
    elif csResp.code != 0:
        logger.error(f"签到失败，错误代码：{csResp.code}，错误信息：{csResp.message}")
        return -1

    logger.info(f"签到成功，今日获得积分：{csResp.baseIntegratedPoint}，连续签到天数：{csResp.continueDay}")
    return csResp.baseIntegratedPoint


def sign_and_save():
    parser = argparse.ArgumentParser(
        description="携程自动签到",
        epilog="例如：python sign.py --cookie 'pt_key=xxx;pt_pin=yyy;'",
    )
    parser.add_argument("--cookie", required=False, help="携程 Cookie，用于身份认证")
    args = parser.parse_args()

    cookie = args.cookie or os.getenv("CTRIP_COOKIE", "")
    logger = get_logger()

    if not cookie:
        logger.error("未提供 Cookie")
        return

    count = sign(logger, cookie)
    if count < 0:
        logger.warning("⚠️ 签到失败，未获得积分")
        return

    current_directory = os.path.dirname(__file__)
    csv_dir = os.path.join(current_directory, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    filepath = os.path.join(csv_dir, "ctrip_sign.csv")
    save_and_clean(
        filepath, logger, ["timestamp", "count"], [get_today_timestamp(), count], 7
    )

    parent_directory = os.path.dirname(current_directory)
    update_readme_with_table(
        logger, filepath, f"{parent_directory}/README.md", "ctrip_sign"
    )


if __name__ == "__main__":
    sign_and_save()
