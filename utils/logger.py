# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-22 00:17:16

import inspect
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler


# ========== 判断当前是否为北京时间 ==========
def is_beijing_time():
    now = datetime.now()
    utc_now = datetime.utcnow()
    offset = now - utc_now
    # 允许一点误差（±1分钟）避免 DST、系统偏差影响
    return abs(offset - timedelta(hours=8)) < timedelta(minutes=1)


# ========== 自定义 Handler（模拟北京时间轮转） ==========
class BeijingTimedRotatingFileHandler(TimedRotatingFileHandler):
    def computeRollover(self, currentTime):
        # 北京时间偏移（8小时）
        beijing_offset = 8 * 60 * 60
        currentTime += beijing_offset
        rolloverAt = super().computeRollover(currentTime)
        return rolloverAt - beijing_offset


# ========== 通用日志工厂 ==========
def get_logger(
    name=None, when="midnight", interval=1, backup_count=7, encoding="utf-8"
):
    # 获取调用者路径
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_dir = os.path.dirname(os.path.abspath(caller_file))

    # 构建 log 目录
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

        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件 handler（自动判断时区）
        if is_beijing_time():
            handler_class = TimedRotatingFileHandler
        else:
            handler_class = BeijingTimedRotatingFileHandler

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
