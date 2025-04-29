# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date: 2025-04-22 00:17:16

import gzip
import inspect
import logging
import os
import re
import shutil
from datetime import datetime, timedelta
from logging import Logger
from logging.handlers import TimedRotatingFileHandler


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
    DATE_PATTERN = re.compile(r".*\.(\d{4}-\d{2}-\d{2})(\.gz)?$")

    def __init__(
        self, *args, backupCount=7, compressBeforeDays=7, deleteBeforeDays=90, **kwargs
    ):
        super().__init__(*args, backupCount=backupCount, **kwargs)
        self.compressBeforeDays = compressBeforeDays
        self.deleteBeforeDays = deleteBeforeDays

        self.doRollover()

    def doRollover(self):
        super().doRollover()
        self.compress_old_logs()
        self.cleanup_very_old_logs()

    def parse_date_from_filename(self, filename):
        match = self.DATE_PATTERN.match(filename)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d").date()
            except Exception:
                return None
        return None

    def compress_old_logs(self):
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        prefix = baseName + "."
        today = datetime.today().date()

        for fileName in fileNames:
            if fileName.startswith(prefix) and not fileName.endswith(".gz"):
                suffix = fileName[len(prefix) :]  # noqa: E203
                if self.extMatch.match(suffix):
                    fullPath = os.path.join(dirName, fileName)
                    file_date = self.parse_date_from_filename(fileName)
                    if file_date and (today - file_date).days > self.compressBeforeDays:
                        gz_filepath = fullPath + ".gz"
                        if not os.path.exists(gz_filepath):
                            with open(fullPath, "rb") as f_in, gzip.open(
                                gz_filepath, "wb"
                            ) as f_out:
                                shutil.copyfileobj(f_in, f_out)
                            os.remove(fullPath)
                            self._log_internal(f"Compressed: {fileName}")

    def cleanup_very_old_logs(self):
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        today = datetime.today().date()

        for fileName in fileNames:
            if fileName.startswith(baseName) and fileName.endswith(".gz"):
                fullPath = os.path.join(dirName, fileName)
                file_date = self.parse_date_from_filename(fileName)
                if file_date and (today - file_date).days > self.deleteBeforeDays:
                    os.remove(fullPath)
                    self._log_internal(f"Deleted old log: {fileName}")

    def _log_internal(self, message):
        try:
            record = logging.LogRecord(
                name="log.internal",
                level=logging.INFO,
                pathname=__file__,
                lineno=0,
                msg=message,
                args=(),
                exc_info=None,
            )
            self.emit(record)
        except Exception:
            pass


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
