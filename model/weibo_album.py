# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-04 00:50:17

from typing import List

from pydantic import BaseModel


class AlbumItem(BaseModel):
    photo_id: str
    uid: int
    pic_host: str
    pic_name: str
    # caption_render: str
    # caption: str
    timestamp: int

    class Config:
        extra = "ignore"


class AlbumData(BaseModel):
    total: int
    photo_list: List[AlbumItem]

    class Config:
        extra = "ignore"


class AlbumResponse(BaseModel):
    result: bool
    code: int
    data: AlbumData

    class Config:
        extra = "ignore"
