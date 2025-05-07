# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-07 22:45:17

from pydantic import BaseModel


class CtripSignResponse(BaseModel):
    code: int
    message: str
    baseIntegratedPoint: int
    continueDay: int

    class Config:
        extra = "ignore"
