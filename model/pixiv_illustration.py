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


class PixivUserTopItem(BaseModel):
    title: str
    url: str
    illustType: int
    userName: str
    id: int
    userId: int
    pageCount: int

    class Config:
        extra = "ignore"


class PixivItemUrl(BaseModel):
    mini: str
    thumb: str
    small: str
    regular: str
    original: str

    class Config:
        extra = "ignore"


class PixivItemUrlInfo(BaseModel):
    viewCount: int  # 浏览数
    likeCount: int  # 点赞数
    bookmarkCount: int  # 收藏数

    title: str
    urls: PixivItemUrl

    class Config:
        extra = "ignore"
