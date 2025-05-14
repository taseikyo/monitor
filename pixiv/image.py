# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-13 31:39:09

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import Logger
from typing import Dict, List
from urllib.parse import urlparse

import requests

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from model.pixiv_illustration import PixivItemUrlInfo  # noqa: E402

MAX_RETRIES = 3
CONCURRENT_LIMIT = 10
IMAGE_QUALITY = ["original", "regular", "small", "thumb_mini"]


class PixivImage:
    """
    PixivImage类，用于获取Pixiv图片的URL信息
    """

    def __init__(self, logger: Logger, pid: int):
        self.logger = logger
        self.pid = pid

    def get_image_urls(self) -> List[str]:
        """
        获取图片所有的URL链接
        """
        headers = {
            "referer": "https://www.pixiv.net/ranking.php",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        url = f"https://www.pixiv.net/ajax/illust/{self.pid}/pages?lang=zh"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            self.logger.info(f"Request URL: {response.url}")
            self.logger.info(f"Response Text: {response.text.replace('\n', '')}")
            resp = response.json()
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode failed: {e}")
            return []

        if not resp:
            self.logger.warning("Empty response.")
            return []

        data = resp.get("body", [])

        urls = []
        for pic in data:
            urls = pic.get("urls", {})
            for x in IMAGE_QUALITY:
                url = urls.get(x, "")
                if url:
                    urls.append(url)
                    break

        self.logger.info(f"pid: {self.pid}, urls: {urls}")
        return urls

    def get_image_info(self) -> PixivItemUrlInfo:
        """
        获取图片的 URL 信息，包括：链接，点赞数，评论数，收藏数
        相比于 get_image_urls 多了图片的统计信息，但是仅拿到第一张图片的 url
        """
        headers = {
            "referer": "https://www.pixiv.net/ranking.php",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        url = f"https://www.pixiv.net/ajax/illust/{self.pid}?lang=zh"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            self.logger.info(f"🔎 Request URL: {response.url}")
            self.logger.info(f"📄 Response Text: {response.text}")
            resp = response.json()
        except requests.RequestException as e:
            self.logger.error(f"❌ Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ JSON decode failed: {e}")
            return None

        if not resp:
            self.logger.warning("⚠️  Empty response.")
            return None

        try:
            return PixivItemUrlInfo.model_validate(resp.get("body", {}))
        except Exception as e:
            self.logger.error(f"❌ Failed to parse PixivItemUrlInfo: {e}")
            return None


def batch_get_image_infos(
    logger: Logger, pids: List[int], max_workers: int = 10
) -> Dict[int, PixivItemUrlInfo]:
    """
    批量获取图片的url信息，包括：链接，点赞数，评论数，收藏数
    :param logger: 日志记录器
    :param pids: 图片 ID 列表
    :param max_workers: 最大线程数
    :return: 图片 ID 和对应的 URL 信息字典
    """
    result = {}
    wroks = [PixivImage(logger, pid) for pid in pids]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(work.get_image_info): work.pid for work in wroks
        }
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                result[pid] = future.result()
            except Exception as e:
                logger.error(f"❌ Failed to get url for pid {pid}: {e}")
                result[pid] = None

    return result


def batch_get_image_urls(
    logger: Logger, pids: List[int], max_workers: int = 10
) -> Dict[int, List[str]]:
    """
    批量获取图片的 URL
    :param logger: 日志记录器
    :param pids: 图片 ID 列表
    :param max_workers: 最大线程数
    :return: 图片 URL 列表
    """
    result = {}
    wroks = [PixivImage(logger, pid) for pid in pids]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(work.get_image_urls): work.pid for work in wroks
        }
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                urls = future.result()
                result[pid] = urls
            except Exception as e:
                logger.error(f"Failed to get urls for pid {pid}: {e}")
                result[pid] = []

    return result


def download_image_stream(logger: Logger, url: str, save_path: str) -> None:
    """
    下载图片
    :param logger: 日志记录器
    :param url: 图片 URL
    :param save_path: 保存路径
    """
    headers = {
        "referer": "https://www.pixiv.net/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, stream=True)
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
    """
    批量下载图片
    :param logger: 日志记录器
    :param urls: 图片 URL 列表
    :param save_paths: 保存路径列表
    :param max_workers: 最大线程数
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_image_stream, logger, url, save_path)
            for url, save_path in zip(urls, save_paths)
        ]
        for future in futures:
            future.result()


def get_url_basename(url: str) -> str:
    parsed_url = urlparse(url)
    basename = os.path.basename(parsed_url.path)
    return basename


def filter_and_save_image_by_map(
    logger: Logger,
    user_id: str,
    basename: str,
    global_map: Dict[str, List[str]],
    local_map: Dict[str, List[str]],
) -> bool:
    """
    检查图片是否已经存在于全局或本地映射中
    :param logger: 日志记录器
    :param user_id: 用户 ID
    :param basename: 图片文件名
    :param global_map: 全局映射
    :param local_map: 本地映射
    :return: 如果图片已经存在于全局或本地映射中，则返回 True，否则返回 False
    """
    if basename in global_map.get(user_id, []):
        logger.info(f"📂 Exists in global, skip: {basename}")
        return True
    if basename in local_map.get(user_id, []):
        logger.info(f"📂 Exists in local, skip: {basename}")
        return True
    else:
        local_map[user_id] = []
    local_map[user_id].append(basename)

    return False
