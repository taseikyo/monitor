# log_utils.py

import gzip
import inspect
import os
import re
import shutil
import sys
from datetime import datetime

from loguru import logger

DATE_PATTERN = re.compile(r".*\.(\d{4}-\d{2}-\d{2})(\.gz)?$")


def compress_and_cleanup_logs(
    log_dir, base_name, compress_before_days=7, delete_before_days=30
):
    today = datetime.today().date()

    for file_name in os.listdir(log_dir):
        # 只处理当前 logger 生成的文件
        if not file_name.startswith(base_name):
            continue

        full_path = os.path.join(log_dir, file_name)
        match = DATE_PATTERN.match(file_name)
        if not match:
            continue

        try:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except Exception:
            continue

        if not file_name.endswith(".gz"):
            if (today - file_date).days > compress_before_days:
                gz_path = full_path + ".gz"
                if not os.path.exists(gz_path):
                    with open(full_path, "rb") as f_in, gzip.open(
                        gz_path, "wb"
                    ) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    os.remove(full_path)
                    logger.info(f"Compressed: {file_name}")
        else:
            if (today - file_date).days > delete_before_days:
                os.remove(full_path)
                logger.info(f"Deleted old log: {file_name}")


def get_loguru_logger(
    name: str = "",
    rotation: str = "00:00",
    retention: str = "7 days",
    compress_before_days: int = 7,
    delete_before_days: int = 30,
    encoding: str = "utf-8",
):
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_dir = os.path.dirname(os.path.abspath(caller_file))

    log_dir = os.path.join(caller_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(caller_file))[0]
    logger_name = name or base_name
    log_file = os.path.join(log_dir, f"{logger_name}.log")

    logger.remove()

    # 控制台 handler，带彩色等级区分
    logger.add(
        sink=sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "<cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # 文件 handler，纯文本日志
    logger.add(
        sink=log_file,
        level="INFO",
        rotation=rotation,
        retention=retention,
        encoding=encoding,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} - {message}",
        enqueue=True,
    )

    compress_and_cleanup_logs(
        log_dir, logger_name, compress_before_days, delete_before_days
    )

    return logger
