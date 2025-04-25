# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-24 23:17:32
# @Ref:    https://github.com/chang-zy/Sina-Album-Crawl-Python


import argparse
import asyncio
import json
import os
import sys
from collections import namedtuple
from typing import List

import aiohttp
import requests
from aiohttp import ClientSession

# 添加项目根目录到 sys.path，确保能导入 bootstrap.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from utils.logger import get_logger  # noqa: E402
from utils.timer import (  # noqa: E402
    get_today_timestamp,
    to_beijing_time,
    to_beijing_time_str,
)

# 定义结构
WBAlbum = namedtuple(
    "WBAlbum", ["caption", "caption_render", "pic_host", "pic_name", "timestamp"]
)

DefaultValues = {
    "caption": "",
    "caption_render": "",
    "pic_host": "",
    "pic_name": "",
    "timestamp": 0,
}


MAX_RETRIES = 3
CONCURRENT_LIMIT = 10


async def download_image(
    session: ClientSession, url: str, save_path: str, sem: asyncio.Semaphore
):
    logger = get_logger()
    if os.path.exists(save_path):
        logger.info(f"📂 已存在，跳过下载: {save_path}")
        return

    async with sem:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"⚠️ 状态码 {resp.status}，第 {attempt} 次重试: {url}")
                        continue
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "wb") as f:
                        while True:
                            chunk = await resp.content.read(1024)
                            if not chunk:
                                break
                            f.write(chunk)
                    logger.info(f"✅ 下载成功: {save_path}")
                    return
            except Exception as e:
                logger.error(f"⚠️ 异常: {url}，第 {attempt} 次重试，错误: {e}")
            await asyncio.sleep(0.5)  # 防止过快重试

        logger.error(f"❌ 最终失败: {url}")


async def download_all_images(ual: List[WBAlbum], uid: str):
    sem = asyncio.Semaphore(CONCURRENT_LIMIT)
    current_directory = os.path.dirname(__file__)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for item in ual:
            url = f"{item.pic_host}/large/{item.pic_name}"
            dt = to_beijing_time(item.timestamp)
            save_dir = os.path.join(
                current_directory, "images", uid, dt.strftime("%Y%m")
            )
            save_path = os.path.join(save_dir, f"{item.timestamp}_{item.pic_name}")
            tasks.append(download_image(session, url, save_path, sem))
        await asyncio.gather(*tasks)


def get_user_album(uid: str, cookie: str, timestamp: int) -> List[WBAlbum]:
    logger = get_logger()
    session = requests.Session()
    if len(uid) == 0 or len(cookie) == 0:
        logger.warning("Empty uid or cookie!")
        return []

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "cookie": cookie,
    }

    logger.info(f"timestamp: {timestamp}")
    should_break = False
    for p in range(1, 10):
        url = (
            f"https://photo.weibo.com/photos/get_all?uid={uid}&count=30&page={p}&type=3"
        )
        try:
            response = session.post(url, headers=headers, timeout=10)
            logger.info(f"Request URL: {response.url}")
            logger.info(
                f"Response Text: {response.text.replace(' ', '').replace('\n', '')}"
            )
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

        data = resp.get("data", {})
        photo_list = data.get("photo_list", [])

        fields = WBAlbum._fields

        wb_album_list = []
        for photo in photo_list:
            item = {key: photo.get(key, DefaultValues[key]) for key in fields}
            wb_album = WBAlbum(**item)
            wb_album_list.append(wb_album)
            if wb_album.timestamp < timestamp:
                should_break = True

        if should_break or len(wb_album_list) == 0:
            break

    return wb_album_list


def get_and_save_photo(uids: List[str]):
    parser = argparse.ArgumentParser(
        description="获取微博图片",
        epilog="例如：python get_and_save_photo.py --cookie 'pt_key=xxx;pt_pin=yyy;'",
    )
    parser.add_argument("--cookie", required=False, help="WB Cookie，用于身份认证")
    args = parser.parse_args()

    cookie = args.cookie or os.getenv("WB_COOKIE", "")
    today = get_today_timestamp()
    for uid in uids:
        ual = get_user_album(uid, cookie, today)
        logger = get_logger()
        if not ual:
            logger.warning(f"{to_beijing_time_str(today)}, {uid} has no photo!")
            continue

        asyncio.run(download_all_images(ual, uid))


if __name__ == "__main__":
    # 萌宠
    uid_animal = ["3186116445", "1749139802"]
    # 明星
    uid_star = ["1669879400", "3261134763", "1676082433"]
    # 表情包
    uid_meme = ["2632260340", "5553432114"]

    uids = uid_animal + uid_star + uid_meme
    get_and_save_photo(uids)
