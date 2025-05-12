# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-27 19:28:54

import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from glob import glob
from logging import Logger
from typing import List
from urllib.parse import urlparse

import requests

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


def get_image_url(logger: Logger, pid: int = 0) -> List[str]:
    if pid == 0:
        return []

    headers = {
        "referer": "https://www.pixiv.net/ranking.php",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    url = f"https://www.pixiv.net/ajax/illust/{pid}/pages?lang=zh"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        logger.info(f"Request URL: {response.url}")
        logger.info(f"Response Text: {response.text.replace('\n', '')}")
        resp = response.json()
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return []

    if not resp:
        logger.warning("Empty response.")
        return []

    data = resp.get("body", [])

    pid_urls = []
    for pic in data:
        urls = pic.get("urls", {})
        for x in IMAGE_QUALITY:
            url = urls.get(x, "")
            if url:
                pid_urls.append(url)
                break

    logger.info(f"pid: {pid}, urls: {pid_urls}")
    return pid_urls


def batch_get_image_urls(
    logger: Logger, pids: List[int], max_workers: int = 10
) -> List[List[str]]:
    """
    批量获取图片的 URL
    :param logger: 日志记录器
    :param pids: 图片 ID 列表
    :param max_workers: 最大线程数
    :return: 图片 URL 列表
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(get_image_url, logger, pid): pid for pid in pids
        }
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                urls = future.result()
                results.append(urls)
            except Exception as e:
                logger.error(f"Failed to get urls for pid {pid}: {e}")
                results.append([])

    return results


def get_url_basename(url: str) -> str:
    parsed_url = urlparse(url)
    basename = os.path.basename(parsed_url.path)
    return basename


def download_image_stream(
    logger: Logger, url: str, save_path: str, session: requests.Session
) -> None:
    headers = {
        "referer": "https://www.pixiv.net/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, headers=headers, stream=True)
            if response.status_code != 200:
                logger.warning(f"⚠️ 状态码 {response.status_code}，第 {attempt} 次重试: {url}")
                continue
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"✅ 下载成功: {os.path.basename(save_path)}")
            return

        except requests.RequestException as e:
            logger.error(f"请求失败: {e}, 尝试重试第 {attempt} 次: {url}")

    logger.error(f"❌ 最终失败: {url}")


def batch_download_images(
    logger: Logger, urls: List[str], save_paths: List[str], max_workers: int = 10
) -> None:
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(download_image_stream, logger, url, save_path, session)
                for url, save_path in zip(urls, save_paths)
            ]
            for future in futures:
                future.result()


def get_and_save_today_rank_image(logger: Logger, mode: str) -> None:
    pixiv_list = rank_today_list(logger, mode=mode, max_page=2)
    pids = [pixiv.illust_id for pixiv in pixiv_list]

    urls_list = batch_get_image_urls(logger, pids, max_workers=10)
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

    for pixiv, urls in zip(pixiv_list, urls_list):
        logger.info(
            f"[{mode}] {pixiv.title} ({pixiv.illust_id} | {pixiv.user_id}): {urls}"
        )
        if str(pixiv.user_id) not in download_images_local_map:
            download_images_local_map[str(pixiv.user_id)] = []

        for url in urls:
            basename = get_url_basename(url)
            if basename in download_images_global_map.get(str(pixiv.user_id), []):
                logger.info(f"📂 已存在于 global，跳过下载: {basename}")
                continue

            if basename in download_images_local_map[(str(pixiv.user_id))]:
                logger.info(f"📂 已存在于 local，跳过下载: {basename}")
                continue

            download_images_local_map[str(pixiv.user_id)].append(basename)
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
    modes = ["daily", "weekly", "monthly", "rookie"]
    logger = get_logger()
    with ThreadPoolExecutor(max_workers=len(modes)) as executor:
        futures = [
            executor.submit(get_and_save_today_rank_image, logger, mode)
            for mode in modes
        ]
        for future in futures:
            future.result()

    merge_all_json_files(logger)
