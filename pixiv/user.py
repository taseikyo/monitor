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
from ranking import batch_download_images, batch_get_image_urls, get_url_basename

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from model.pixiv_illustration import PixivItemUrlInfo, PixivUserTopItem  # noqa: E402
from utils.logger import get_logger  # noqa: E402

CONCURRENT_LIMIT = 10


def get_user_top_items(logger: Logger, user_id: str) -> List[PixivUserTopItem]:
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
    try:
        response = session.get(base_url, params=payload, headers=headers, timeout=10)
        logger.info(f"Request URL: {response.url}")
        logger.info(f"Response Text: {response.text}")
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return []

    try:
        resp = response.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return []

    if not resp:
        logger.warning("Empty response.")
        return []

    illusts = resp.get("body", {}).get("illusts", {})
    if not illusts:
        logger.warning("No illustrations found.")
        return []

    result = []
    for pid, illust in illusts.items():
        item = PixivUserTopItem.model_validate(illust)
        result.append(item)

    return result


def get_image_url_info(logger: Logger, pid: int) -> PixivItemUrlInfo:
    """
    获取图片的url信息，包括：链接，点赞数，评论数，收藏数
    相比于 rankng.py: get_image_url() 多了图片的统计信息，但是仅拿到第一张图片的 url
    """
    if pid == 0:
        return None
    headers = {
        "referer": "https://www.pixiv.net/ranking.php",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    url = f"https://www.pixiv.net/ajax/illust/{pid}?lang=zh"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"Request URL: {response.url}")
        logger.info(f"Response Text: {response.text.replace('\n', '')}")
        resp = response.json()
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return None

    if not resp:
        logger.warning("Empty response.")
        return None

    try:
        return PixivItemUrlInfo.model_validate(resp.get("body", {}))
    except Exception as e:
        logger.error(f"Failed to parse PixivItemUrlInfo: {e}")
        return None


def download_user_top_images(
    logger: Logger, user_id: str, download_images_global_map: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    all_urls = []
    all_save_paths = []
    download_images_local_map = {}
    current_directory = os.path.dirname(__file__)
    pixiv_list = get_user_top_items(logger, user_id)
    pids = [pixiv.id for pixiv in pixiv_list]
    logger.info(f"Processing user: {user_id}, pids: {pids}")
    urls_list = batch_get_image_urls(logger, pids, CONCURRENT_LIMIT)
    for pixiv, urls in zip(pixiv_list, urls_list):
        if len(urls) > 1:
            logger.warning(f"`{pixiv.id}` has multiple URLs: {len(urls)}")
            continue
        for url in urls:
            basename = get_url_basename(url)
            if basename in download_images_global_map.get(str(pixiv.userId), []):
                logger.info(f"📂 Exists in global, skip: {basename}")
                continue
            if basename in download_images_local_map.get(str(pixiv.userId), []):
                logger.info(f"📂 Exists in local, skip: {basename}")
                continue
            else:
                download_images_local_map[str(pixiv.userId)] = []
            download_images_local_map[str(pixiv.userId)].append(basename)
            save_dir = os.path.join(current_directory, "images", f"{pixiv.userId}")
            save_path = os.path.join(save_dir, f"{basename}")
            all_urls.append(url)
            all_save_paths.append(save_path)
    try:
        if len(all_urls) > 0:
            batch_download_images(logger, all_urls, all_save_paths, CONCURRENT_LIMIT)
        return download_images_local_map
    except Exception as e:
        logger.error(f"Error downloading images: {e}")
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

    def process_user(uid: str):
        try:
            local_map = download_user_top_images(
                logger, uid, download_images_global_map
            )
            with map_lock:
                for user_id, images in local_map.items():
                    if user_id not in download_images_global_map:
                        download_images_global_map[user_id] = []
                    download_images_global_map[user_id].extend(images)
        except Exception as e:
            logger.error(f"Error processing user {uid}: {e}")

    with ThreadPoolExecutor(max_workers=CONCURRENT_LIMIT) as executor:
        executor.map(process_user, list(download_images_global_map.keys()))

    with open(download_images_map_global_filepath, "w") as f:
        json.dump(download_images_global_map, f, ensure_ascii=False, indent=0)
