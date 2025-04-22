# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-22 19:05:25

from datetime import datetime
from datetime import time as dtime
from zoneinfo import ZoneInfo


def get_today_timestamp() -> int:
    # 获取当前北京时间的日期
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    # 构造当天零点的 datetime 对象（仍在北京时间）
    zero_time = datetime.combine(
        now.date(), dtime.min, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    # 转换为时间戳（UTC+0 秒数）
    return int(zero_time.timestamp())
