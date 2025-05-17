# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-17 14:30:17

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from threading import Lock
from typing import List

import requests

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from user import download_user_top_images  # noqa: E402

import bootstrap  # noqa: F401, E402
from model.pixiv_illustration import (  # noqa: E402
    PixivFollowingInfo,
    PixivFollowingUserInfo,
)
from utils.logger import get_logger  # noqa: E402


def get_user_following(
    logger: Logger, user_id: str, cookie: str, max_page: int = 10
) -> List[PixivFollowingUserInfo]:
    if len(user_id) == 0 or len(cookie) == 0:
        logger.error("❌ Invalid user ID or empty cookie.")
        return []

    session = requests.Session()
    headers = {
        "referer": "https://www.pixiv.net",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "cookie": cookie,
    }
    payload = {
        "offset": 0,
        "limit": 30,
        "rest": "show",
        "tag": "",
        "acceptingRequests": 0,
        "lang": "zh",
    }
    base_url = f"https://www.pixiv.net/ajax/user/{user_id}/following"
    count = 30
    result = []
    for i in range(max_page):
        payload["offset"] = count * i
        payload["limit"] = count
        logger.info(f"🌐 Page {i+1} with offset {payload['offset']}...")
        try:
            response = session.get(
                base_url, params=payload, headers=headers, timeout=10
            )
            logger.info(f"🌐 Request URL: {response.url}")
            logger.info(f"📄 Response Text: {response.text}")
        except requests.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return []

        try:
            resp = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode failed: {e}")
            return []

        if not resp or not resp.get("body", {}):
            logger.warning("❌ Empty response.")
            return []

        pfiResp = PixivFollowingInfo.model_validate(resp.get("body", {}))

        result += pfiResp.users
        logger.info(f"📄 Page {i+1}, user: {len(pfiResp.users)}...")

        if count * (i + 1) >= pfiResp.total:
            logger.info("✅ All pages fetched.")
            break

    return result


if __name__ == "__main__":
    logger = get_logger()
    user_id = os.getenv("PIXIV_UID", "")
    cookie = os.getenv("PIXIV_COOKIE", "")
    ufs = get_user_following(logger, user_id, cookie)

    user_ids = [uf.userId for uf in ufs]
    logger.info(f"✅ Found {len(user_ids)} following users.")

    current_directory = os.path.dirname(__file__)
    download_images_map_global_filepath = f"{current_directory}/rank.json"
    download_images_global_map = {}

    if os.path.exists(download_images_map_global_filepath):
        with open(download_images_map_global_filepath, "r") as f:
            download_images_global_map = json.load(f)

    map_lock = Lock()
    favorite_count = 5000  # 仅下载红心数超过5k的图片

    def process_user(uid: str):
        try:
            local_map = download_user_top_images(
                logger, uid, favorite_count, download_images_global_map
            )
            with map_lock:
                for user_id, images in local_map.items():
                    if user_id not in download_images_global_map:
                        download_images_global_map[user_id] = []
                    download_images_global_map[user_id].extend(images)
        except Exception as e:
            logger.error(f"❌ Error processing user {uid}: {e}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_user, user_ids)

    with open(download_images_map_global_filepath, "w") as f:
        json.dump(download_images_global_map, f, ensure_ascii=False, indent=0)
    logger.info(f"✅ Finished. Updated {download_images_map_global_filepath}")
