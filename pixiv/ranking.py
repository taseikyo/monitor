# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-27 19:28:54

import json
import os
import sys
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
from typing import List
from urllib.parse import urlparse

import requests

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from utils.logger import get_logger  # noqa: E402

# 定义 namedtuple
Illustration = namedtuple(
    "Illustration",
    [
        "title",
        "url",
        "illust_type",
        "user_name",
        "illust_id",
        "user_id",
        "illust_page_count",
    ],
)

DefaultValues = {
    "title": "",
    "url": "",
    "illust_type": "",
    "user_name": "",
    "illust_id": 0,
    "user_id": 0,
    "illust_page_count": "1",
}

MAX_RETRIES = 3
CONCURRENT_LIMIT = 10


def rank_today_list(
    date: str = "", mode: str = "daily", max_page: int = 10
) -> List[Illustration]:
    logger = get_logger()
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

        contents = resp.get("contents", [])
        fields = Illustration._fields
        for content in contents:
            tmp = {key: content.get(key, DefaultValues.get(key)) for key in fields}
            item = Illustration(**tmp)
            # 超过一张图的不要
            if int(item.illust_page_count) > 1:
                logger.warning(
                    f"id: {item.illust_id} count {item.illust_page_count} skip!"
                )
                continue
            pixiv_list.append(item)
            logger.info(f"item: {item}")

    return pixiv_list


def get_image_url(pid: int = 0) -> List[str]:
    if pid == 0:
        return []

    logger = get_logger()
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
    image_quality = ["original", "regular", "small", "thumb_mini"]

    pid_urls = []
    for pic in data:
        urls = pic.get("urls", {})
        for x in image_quality:
            url = urls.get(x, "")
            if url:
                pid_urls.append(url)
                break

    logger.info(f"pid: {pid}, urls: {pid_urls}")
    return pid_urls


def batch_get_image_urls(pids: List[int], max_workers: int = 10) -> List[List[str]]:
    results = []
    logger = get_logger()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {executor.submit(get_image_url, pid): pid for pid in pids}
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
    # 解析URL
    parsed_url = urlparse(url)

    # 从URL路径中提取文件名
    basename = os.path.basename(parsed_url.path)

    return basename


def download_image_stream(url: str, save_path: str, session: requests.Session) -> None:
    logger = get_logger()
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
                for chunk in response.iter_content(chunk_size=8192):  # 分块写入
                    f.write(chunk)
            logger.info(f"✅ 下载成功: {os.path.basename(save_path)}")
            return

        except requests.RequestException as e:
            logger.error(f"请求失败: {e}, 尝试重试第 {attempt} 次: {url}")

    logger.error(f"❌ 最终失败: {url}")


def batch_download_images(
    urls: List[str], save_paths: List[str], max_workers: int = 10
) -> None:
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 使用线程池并发下载
            futures = [
                executor.submit(download_image_stream, url, save_path, session)
                for url, save_path in zip(urls, save_paths)
            ]
            # 等待所有任务完成
            for future in futures:
                future.result()


def get_and_save_today_rank_image(mode: str) -> None:
    logger = get_logger()
    pixiv_list = rank_today_list(mode=mode, max_page=2)
    pids = [pixiv.illust_id for pixiv in pixiv_list]

    urls_list = batch_get_image_urls(pids, max_workers=10)
    current_directory = os.path.dirname(__file__)
    all_urls = []
    all_save_paths = []

    # 已经下载的图片的 JSON 历史
    already_downlaod_images_map = {}
    already_downlaod_images_map_filepath = f"{current_directory}/rank.json"
    with open(already_downlaod_images_map_filepath, "r") as f:
        already_downlaod_images_map = json.load(f)

    for pixiv, urls in zip(pixiv_list, urls_list):
        logger.info(
            f"[{mode}] {pixiv.title} ({pixiv.illust_id} | {pixiv.user_id}): {urls}"
        )
        if pixiv.user_id not in already_downlaod_images_map:
            already_downlaod_images_map[pixiv.user_id] = []

        for url in urls:
            basename = get_url_basename(url)
            if basename in already_downlaod_images_map[pixiv.user_id]:
                logger.info(f"📂 已存在，跳过下载: {basename}")
                continue

            already_downlaod_images_map[pixiv.user_id].append(basename)
            save_dir = os.path.join(current_directory, "images", f"{pixiv.user_id}")
            save_path = os.path.join(save_dir, f"{basename}")
            all_urls.append(url)
            all_save_paths.append(save_path)

    # 更新下载的图片的 JSON 历史
    with open(already_downlaod_images_map_filepath, "w") as f:
        json.dump(already_downlaod_images_map, f, ensure_ascii=False, indent=0)

    batch_download_images(all_urls, all_save_paths, max_workers=CONCURRENT_LIMIT)


if __name__ == "__main__":
    modes = ["daily", "weekly", "monthly", "rookie"]
    with Pool(processes=len(modes)) as pool:
        pool.map(get_and_save_today_rank_image, modes)
