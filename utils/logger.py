# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date: 2025-04-22 00:17:16

import gzip
import inspect
import logging
import os
import shutil
from datetime import datetime, timedelta
from logging import Logger
from logging.handlers import TimedRotatingFileHandler
from typing import List, Tuple


def is_beijing_time() -> bool:
    """
    判断当前系统时间是否接近北京时间 (UTC+8)。

    允许 1 分钟以内的误差，防止系统时钟误差或夏令时 (DST) 影响。

    Returns:
        bool: 若接近北京时间，返回 True，否则返回 False。
    """
    now = datetime.now()
    utc_now = datetime.utcnow()
    offset = now - utc_now
    # 容忍 1 分钟误差
    return abs(offset - timedelta(hours=8)) < timedelta(minutes=1)


class SmartCompressAndCleanupTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    扩展版的 TimedRotatingFileHandler：
    - 轮转日志后自动压缩旧日志为 .gz 文件
    - 自动清理超过指定天数的压缩日志
    """

    def doRollover(self) -> None:
        """
        重写轮转方法，增加压缩和清理逻辑。
        """
        super().doRollover()
        self.compress_old_logs()
        self.cleanup_very_old_logs()

    def compress_old_logs(self) -> None:
        """
        将超过保留数量 (backupCount) 的旧日志文件压缩为 .gz 格式，并删除原文件。
        """
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        prefix = base_name + "."
        prefix_len = len(prefix)

        # 筛选出符合扩展名模式且未压缩的日志文件
        logs: List[Tuple[datetime, str]] = []
        for file_name in file_names:
            if file_name.startswith(prefix) and not file_name.endswith(".gz"):
                suffix = file_name[prefix_len:]
                if self.extMatch.match(suffix):
                    full_path = os.path.join(dir_name, file_name)
                    mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                    logs.append((mtime, full_path))

        logs.sort()

        # 需要压缩的文件（超过保留数的）
        logs_to_compress = (
            logs[: -self.backupCount] if len(logs) > self.backupCount else []
        )

        for _, filepath in logs_to_compress:
            gz_filepath = filepath + ".gz"
            if not os.path.exists(gz_filepath):
                with open(filepath, "rb") as f_in, gzip.open(
                    gz_filepath, "wb"
                ) as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(filepath)
                self._log_info(f"Compressed and removed original: {filepath}")

    def cleanup_very_old_logs(self, max_days: int = 90) -> None:
        """
        清理超过 max_days 天的压缩日志文件 (.gz)。

        Args:
            max_days (int): 保留的最大天数，默认 90 天。
        """
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        now = datetime.now()
        expire_time = now - timedelta(days=max_days)

        for file_name in file_names:
            if file_name.startswith(base_name) and file_name.endswith(".gz"):
                full_path = os.path.join(dir_name, file_name)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                if file_mtime < expire_time:
                    os.remove(full_path)
                    self._log_info(f"Deleted old compressed log: {full_path}")

    def _log_info(self, message: str) -> None:
        """
        内部辅助函数，直接向当前日志流写入一条 INFO 级别的记录。
        用于自身处理日志（压缩、清理）的反馈，而不会打扰主 logger。

        Args:
            message (str): 要写入的日志内容。
        """
        record = self.formatter.format(
            logging.LogRecord(
                name="internal",
                level=logging.INFO,
                pathname=__file__,
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )
        )
        self.stream.write(record + "\n")
        self.flush()


def get_logger(
    name: str = "",
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 7,
    encoding: str = "utf-8",
) -> Logger:
    """
    获取一个预配置的 Logger：
    - 控制台输出（INFO及以上）
    - 文件输出（DEBUG及以上）
    - 日志每天轮转，轮转后自动压缩并清理超时日志

    Args:
        name (str): Logger 名称，默认取调用脚本文件名。
        when (str): 轮转时间单位（默认每天 "midnight"）。
        interval (int): 轮转间隔数量，配合 when 使用。
        backup_count (int): 文件保留数量，超过后触发压缩。
        encoding (str): 写日志文件的编码，默认 utf-8。

    Returns:
        Logger: 配置好的 Logger 对象。
    """
    # 获取调用者文件路径
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_dir = os.path.dirname(os.path.abspath(caller_file))

    # 日志目录
    log_dir = os.path.join(caller_dir, "log")
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件路径与 logger 名称
    base_name = os.path.splitext(os.path.basename(caller_file))[0]
    log_file = os.path.join(log_dir, f"{base_name}.log")
    logger_name = name or base_name
    logger = logging.getLogger(logger_name)

    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        # 日志格式
        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s"
        )

        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件 handler
        file_handler = SmartCompressAndCleanupTimedRotatingFileHandler(
            filename=log_file,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y-%m-%d"  # 文件名日期后缀
        logger.addHandler(file_handler)

    return logger
