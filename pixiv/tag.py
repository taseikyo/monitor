# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-17 15:51:59

import json
import os
import sys
from logging import Logger
from typing import List

import requests

# 添加项目根目录到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import bootstrap  # noqa: F401, E402
from model.pixiv_illustration import (  # noqa: E402
    PixivTagItemInfo,
    PixivTagItemRespInfo,
)


def get_tag_pid_info(
    logger: Logger, tag: str, max_page: int = 10
) -> List[PixivTagItemInfo]:
    if len(tag) == 0:
        logger.error("❌ Empty tag.")
        return []

    session = requests.Session()
    headers = {
        "referer": "https://www.pixiv.net",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    payload = {
        "word": tag,
        "order": "date_d",
        "mode": "all",
        "p": 1,
        "csw": 0,
        "s_mode": "s_tag_full",
        "type": "all",
        "lang": "zh",
    }
    base_url = f"https://www.pixiv.net/ajax/search/artworks/{tag}"
    result = []
    for page in range(1, max_page + 1):
        payload["p"] = page
        try:
            response = session.get(
                base_url, params=payload, headers=headers, timeout=10
            )
            logger.info(f"🌐 Request URL: {response.url}, page: {page}")
            resp = response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode failed: {e}")
            return result

        if not resp:
            logger.warning("⚠️ Empty response.")
            return result

        illustManga = resp.get("body", {}).get("illustManga", {})

        ptiResp = PixivTagItemRespInfo.model_validate(illustManga)
        result.extend(ptiResp.data)

        if page >= ptiResp.total:
            break

    return result
