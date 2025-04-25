# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-23 19:08:46
# @Desc:   将 CSV 转换为 Markdown 表格，并插入 README 指定区域

import csv
import logging

from timer import to_beijing_time_str


def csv_to_markdown_table(csv_path: str) -> str:
    """
    读取 CSV 文件并将其内容转换为 Markdown 表格，默认第一列为时间戳。

    参数:
        csv_path (str): CSV 文件路径

    返回:
        str: Markdown 表格内容
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if not rows:
        return ""

    headers = rows[0]
    header_line = "| " + " | ".join(headers) + " |"
    divider_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    data_lines = []
    for row in rows[1:]:
        formatted_row = []
        for i, val in enumerate(row):
            if i == 0:  # 默认第一列为时间戳
                try:
                    ts = int(val)
                    val = to_beijing_time_str(ts)
                except Exception:
                    pass
            formatted_row.append(val)
        data_lines.append("| " + " | ".join(formatted_row) + " |")

    return "\n".join([header_line, divider_line] + data_lines)


def update_readme_with_table(
    logger: logging.Logger, csv_path: str, readme_path: str, section_id: str
) -> None:
    """
    将 Markdown 表格内容插入 README 文件指定的标记区域。

    参数:
        csv_path (str): 要插入的 Markdown 表格内容
        readme_path (str): README 文件路径
        section_id (str): 章节 ID，找到该插入的位置
    """
    table_md = csv_to_markdown_table(csv_path)
    if len(table_md) == 0:
        logger.warn("empty csv data")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 构造动态标记
    start_tag = f"<!-- {section_id}-start -->"
    end_tag = f"<!-- {section_id}-end -->"

    start_index = content.find(start_tag)
    end_index = content.find(end_tag)

    if start_index == -1 or end_index == -1 or start_index > end_index:
        logger.error(f"invalid section_id: {section_id} ")
        return

    # 插入内容，保留原标记
    new_content = (
        content[: start_index + len(start_tag)]
        + "\n\n"
        + table_md
        + "\n\n"
        + content[end_index:]
    )

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
