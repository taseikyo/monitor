# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-10 01:34:21

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from threading import Lock
from typing import Dict, List

import requests
from image import (
    batch_download_images,
    batch_get_image_infos,
    filter_and_save_image_by_map,
    get_url_basename,
)

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from model.pixiv_illustration import PixivUserTopItem  # noqa: E402
from utils.logger import get_logger  # noqa: E402

CONCURRENT_LIMIT = 10


def get_user_top_items(logger: Logger, user_id: str) -> Dict[int, PixivUserTopItem]:
    session = requests.Session()
    headers = {
        "referer": "https://www.pixiv.net/ranking.php",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    base_url = f"https://www.pixiv.net/ajax/user/{user_id}/profile/top"
    payload = {
        "lang": "zh",
        "sensitiveFilterMode": "userSetting",
    }
    result = {}
    try:
        response = session.get(base_url, params=payload, headers=headers, timeout=10)
        logger.info(f"🌐 Request URL: {response.url}")
        resp = response.json()
    except requests.RequestException as e:
        logger.info(f"📄 Response Text: {response.text}")
        logger.error(f"❌ Request failed: {e}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode failed: {e}")
        return result

    if not resp:
        logger.warning("⚠️ Empty response.")
        return result

    illusts = resp.get("body", {}).get("illusts", {})
    if not illusts:
        logger.warning("⚠️ No illustrations found.")
        return result

    for pid, illust in illusts.items():
        item = PixivUserTopItem.model_validate(illust)
        result[int(pid)] = item

    logger.info(f"✅ Found {len(result)} top illustrations for user {user_id}")
    return result


def download_user_top_images(
    logger: Logger,
    user_id: str,
    favorite_count: int,
    download_images_global_map: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    download_images_local_map = {}
    current_directory = os.path.dirname(__file__)
    user_top_images = get_user_top_items(logger, user_id)
    pids = list(user_top_images.keys())
    logger.info(f"🚀 Processing user: {user_id}, pids: {pids}")

    infoMap = batch_get_image_infos(logger, pids, CONCURRENT_LIMIT)
    to_be_downloaded_pids = []
    urls = []
    for pid, info in infoMap.items():
        if not info:
            logger.warning(f"⚠️ Failed to get image info for pid {pid}")
            continue

        # 过滤掉多页的图片
        if info.pageCount > 1:
            logger.warning(f"📖 {pid} has {info.pageCount} pages, skip!")
            continue

        if info.bookmarkCount < favorite_count:
            logger.warning(f"💔 {pid}' favorite count: {info.bookmarkCount}, skip!")
            continue

        url = info.urls.get_url()
        if len(url) == 0:
            logger.warning(f"⚠️ {pid} has no valid URL, skip!")
            continue
        urls.append(url)
        to_be_downloaded_pids.append(pid)

    pixiv_list = [user_top_images[k] for k in to_be_downloaded_pids]
    all_urls = []
    all_save_paths = []
    for pixiv, url in zip(pixiv_list, urls):
        basename = get_url_basename(url)
        if filter_and_save_image_by_map(
            logger,
            str(pixiv.userId),
            basename,
            download_images_global_map,
            download_images_local_map,
        ):
            continue
        save_dir = os.path.join(current_directory, "images", f"{pixiv.userId}")
        save_path = os.path.join(save_dir, f"{basename}")
        all_urls.append(url)
        all_save_paths.append(save_path)
    try:
        if len(all_urls) > 0:
            logger.info(
                f"📥 Start downloading {len(all_urls)} images for user {user_id}"
            )
            batch_download_images(logger, all_urls, all_save_paths, CONCURRENT_LIMIT)
        return download_images_local_map
    except Exception as e:
        logger.error(f"❌ Error downloading images: {e}")
        return {}


def main():
    logger = get_logger()

    current_directory = os.path.dirname(__file__)
    download_images_map_global_filepath = f"{current_directory}/rank.json"
    download_images_global_map = {}

    if os.path.exists(download_images_map_global_filepath):
        with open(download_images_map_global_filepath, "r") as f:
            download_images_global_map = json.load(f)

    map_lock = Lock()
    favorite_count = 5000  # 仅下载红心数超过5k的图片
    user_ranking_times = 10  # 上榜10次的用户才配下载

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

    user_ids = [
        uid
        for uid, images in download_images_global_map.items()
        if len(images) > user_ranking_times
    ]
    logger.info(f"👥 Processing {len(user_ids)} users")
    with ThreadPoolExecutor(max_workers=CONCURRENT_LIMIT) as executor:
        executor.map(process_user, user_ids)

    with open(download_images_map_global_filepath, "w") as f:
        json.dump(download_images_global_map, f, ensure_ascii=False, indent=0)
    logger.info(f"✅ Finished. Updated {download_images_map_global_filepath}")


if __name__ == "__main__":
    main()
