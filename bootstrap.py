# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-04-22 00:15:01
# @Desc:   添加指定目录为 path
import os
import sys

PROJECT_DIRS = ["utils", "model"]


def init():
    project_root = os.path.abspath(os.path.dirname(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    for directory in PROJECT_DIRS:
        dir_path = os.path.join(project_root, directory)
        if dir_path not in sys.path:
            sys.path.insert(0, dir_path)


init()
