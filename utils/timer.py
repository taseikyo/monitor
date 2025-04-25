# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-22 19:05:25

from datetime import datetime
from datetime import time as dtime
from datetime import timedelta, timezone
from typing import Union
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


def to_beijing_time_str(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Shanghai")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def to_beijing_time(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Shanghai"))


def format_timestamp_with_timezone(
    ts: Union[int, float],
    from_offset_hours: int = 0,
    to_offset_hours: int = 0,
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """
    将时间戳从一个时区转换到另一个时区，并格式化输出为字符串。

    参数:
        ts (int | float): 时间戳（来源于 from_offset_hours 时区）
        from_offset_hours (int): 来源时区的小时偏移量（如北京时间为 8，UTC 为 0）
        to_offset_hours (int): 目标时区的小时偏移量
        fmt (str): 格式化字符串，默认格式为 "%Y-%m-%d %H:%M:%S"

    返回:
        str: 目标时区下格式化的时间字符串
    """
    from_tz = timezone(timedelta(hours=from_offset_hours))
    to_tz = timezone(timedelta(hours=to_offset_hours))

    # 使用来源时区创建 datetime 对象
    dt = datetime.fromtimestamp(ts, tz=from_tz)

    # 转换为目标时区
    dt_converted = dt.astimezone(to_tz)

    # 格式化为字符串
    return dt_converted.strftime(fmt)
