# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-27 19:28:54

import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from glob import glob
from logging import Logger
from typing import List

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
from model.pixiv_illustration import PixivItem, PixivResponse  # noqa: E402
from utils.logger import get_logger  # noqa: E402

MAX_RETRIES = 3
CONCURRENT_LIMIT = 10
IMAGE_QUALITY = ["original", "regular", "small", "thumb_mini"]


def rank_today_list(
    logger: Logger, date: str = "", mode: str = "daily", max_page: int = 10
) -> List[PixivItem]:
    session = requests.Session()
    headers = {
        "referer": "https://www.pixiv.net/ranking.php",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    base_url = "https://www.pixiv.net/ranking.php"
    payload = {
        "mode": mode,
        "format": "json",
        "p": "1",
    }
    if date:
        payload["date"] = date

    pixiv_list = []
    for p in range(1, max_page + 1):
        payload["p"] = str(p)
        try:
            response = session.get(
                base_url, params=payload, headers=headers, timeout=10
            )
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

        pixivResponse = PixivResponse.model_validate(resp)
        for content in pixivResponse.contents:
            if content.illust_page_count > 1:
                logger.warning(
                    f"id: {content.illust_id} count {content.illust_page_count} skip!"
                )
                continue

            pixiv_list.append(content)

    return pixiv_list


def download_today_rank_image(logger: Logger, mode: str, favorite_count: int) -> None:
    pixiv_list = rank_today_list(logger, mode=mode, max_page=2)
    pids = [pixiv.illust_id for pixiv in pixiv_list]

    infoMap = batch_get_image_infos(logger, pids, CONCURRENT_LIMIT)
    to_be_downloaded_pids = []
    urls = []
    for pid, info in infoMap.items():
        if not info:
            logger.warning(f"⚠️  Failed to get image info for pid {pid}")
            continue

        # 过滤掉多页的图片
        if info.pageCount > 1:
            logger.info(f"📖 {pid} has {info.pageCount} pages, skip!")
            continue

        if info.bookmarkCount < favorite_count:
            logger.info(f"💔 {pid}' favorite count: {info.bookmarkCount}, skip!")
            continue

        url = info.urls.get_url()
        if len(url) == 0:
            logger.warning(f"⚠️ {pid} has no valid URL, skip!")
            continue
        urls.append(url)
        to_be_downloaded_pids.append(pid)

    current_directory = os.path.dirname(__file__)
    all_urls = []
    all_save_paths = []

    # 已经下载的图片的 JSON 历史
    download_images_local_map = {}
    download_images_global_map = {}
    download_images_map_local_filepath = f"{current_directory}/rank_{mode}.json"
    download_images_map_global_filepath = f"{current_directory}/rank.json"
    if os.path.exists(download_images_map_local_filepath):
        with open(download_images_map_local_filepath, "r") as f:
            download_images_local_map = json.load(f)
    if os.path.exists(download_images_map_global_filepath):
        with open(download_images_map_global_filepath, "r") as f:
            download_images_global_map = json.load(f)

    for pixiv, url in zip(pixiv_list, urls):
        basename = get_url_basename(url)
        if filter_and_save_image_by_map(
            logger,
            str(pixiv.user_id),
            basename,
            download_images_global_map,
            download_images_local_map,
        ):
            continue
        save_dir = os.path.join(current_directory, "images", f"{pixiv.user_id}")
        save_path = os.path.join(save_dir, f"{basename}")
        all_urls.append(url)
        all_save_paths.append(save_path)

    with open(download_images_map_local_filepath, "w") as f:
        json.dump(download_images_local_map, f, ensure_ascii=False, indent=0)

    batch_download_images(
        logger, all_urls, all_save_paths, max_workers=CONCURRENT_LIMIT
    )


def merge_all_json_files(logger: Logger) -> None:
    current_directory = os.path.dirname(__file__)
    json_files = glob(os.path.join(current_directory, "rank*.json"))
    output_filepath = os.path.join(current_directory, "rank.json")
    merged = defaultdict(set)

    for file in json_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if isinstance(v, list):
                    merged[k].update(v)
                else:
                    logger.warning(f"Value for key '{k}' in {file} is not a list")
        except Exception as e:
            logger.error(f"Error processing file {file}: {e}")

    try:
        result = {k: sorted(list(v)) for k, v in merged.items()}
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=0)
        logger.info(f"Merge completed. Output saved to {output_filepath}")
    except Exception as e:
        logger.error(f"Error writing output file: {e}")


if __name__ == "__main__":
    modes = ["daily", "weekly", "monthly", "rookie", "original", "daily_ai"]
    logger = get_logger()
    favorite_count = 1000  # 仅下载红心数超过1k的图片
    with ThreadPoolExecutor(max_workers=len(modes)) as executor:
        futures = [
            executor.submit(download_today_rank_image, logger, mode, favorite_count)
            for mode in modes
        ]
        for future in futures:
            future.result()

    merge_all_json_files(logger)
