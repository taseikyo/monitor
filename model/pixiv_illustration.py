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

    def get_url(self) -> str:
        url = ""
        if self.original:
            url = self.original
        elif self.regular:
            url = self.regular
        elif self.small:
            url = self.small
        elif self.thumb:
            url = self.thumb
        elif self.mini:
            url = self.mini

        return url


class PixivItemUrlInfo(BaseModel):
    viewCount: int  # 浏览数
    likeCount: int  # 点赞数
    bookmarkCount: int  # 收藏数，红心数

    title: str
    urls: PixivItemUrl

    pageCount: int  # 图片数量

    illustId: str

    class Config:
        extra = "ignore"


class PixivFollowingUserInfo(BaseModel):
    userId: str
    userName: str

    class Config:
        extra = "ignore"


class PixivFollowingInfo(BaseModel):
    total: int
    users: List[PixivFollowingUserInfo]

    class Config:
        extra = "ignore"


class PixivTagItemInfo(BaseModel):
    userId: str
    UserName: str

    id: str
    title: str

    class Config:
        extra = "ignore"


class PixivTagItemRespInfo(BaseModel):
    data: List[PixivTagItemInfo]
    lastPage: int
    total: int
