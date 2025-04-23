# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-22 00:17:16

import inspect
import logging
import os
from datetime import datetime, timedelta
from logging import Logger
from logging.handlers import TimedRotatingFileHandler


def is_beijing_time() -> bool:
    """
    判断当前系统时间是否与北京时间同步（UTC+8）。

    返回:
        bool: 如果当前系统时间接近北京时间，则返回 True。
    """
    now = datetime.now()
    utc_now = datetime.utcnow()
    offset = now - utc_now
    # 允许 1 分钟误差范围，以避免 DST 或系统时间误差干扰
    return abs(offset - timedelta(hours=8)) < timedelta(minutes=1)


class BeijingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    基于北京时间的日志轮转 handler，用于在非 UTC+8 时区模拟北京时间行为。
    """

    def computeRollover(self, currentTime: int) -> int:
        """
        修改日志轮转的时间点，使其按照北京时间计算。
        """
        beijing_offset = 8 * 60 * 60  # 北京时间比 UTC 快 8 小时
        currentTime += beijing_offset
        rolloverAt = super().computeRollover(currentTime)
        return rolloverAt - beijing_offset


def get_logger(
    name: str = "",
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    encoding: str = "utf-8",
) -> Logger:
    """
    获取一个支持控制台输出和按天轮转的日志记录器。

    参数:
        name (str): logger 名称，默认为调用脚本的文件名。
        when (str): 日志轮转的时间单位，默认为 "midnight"（每天轮转）。
        interval (int): 轮转间隔数量（与 `when` 联合使用）。
        backup_count (int): 最多保留的历史日志文件数量。
        encoding (str): 写入日志文件的编码方式。

    返回:
        logging.Logger: 配置好的 logger 实例。
    """
    # 获取调用者所在文件路径
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_dir = os.path.dirname(os.path.abspath(caller_file))

    # 创建 log 目录
    log_dir = os.path.join(caller_dir, "log")
    os.makedirs(log_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(caller_file))[0]
    log_file = os.path.join(log_dir, f"{base_name}.log")
    logger_name = name or base_name
    logger = logging.getLogger(logger_name)

    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s"
        )

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件日志输出（判断是否需要用北京时间轮转）
        handler_class = (
            TimedRotatingFileHandler
            if is_beijing_time()
            else BeijingTimedRotatingFileHandler
        )
        file_handler = handler_class(
            filename=log_file,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y-%m-%d"
        logger.addHandler(file_handler)

    return logger
