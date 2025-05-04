# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-04 12:23:17

from typing import List

from pydantic import BaseModel


class PixivItem(BaseModel):
    title: str
    url: str
    illust_type: str
    user_name: str
    illust_id: int
    user_id: int
    illust_page_count: int

    class Config:
        extra = "ignore"


class PixivResponse(BaseModel):
    date: str
    prev_date: str
    page: int
    mode: str
    contents: List[PixivItem]

    class Config:
        extra = "ignore"
