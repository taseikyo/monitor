# -*- coding: utf-8 -*-
# @Author: Lewis Tian
# @Date:   2025-05-02 13:44:19

import hashlib
import math
import os
import pickle

import bitarray


class BloomFilter:
    def __init__(
        self, items: list[str] = [], expected_items=1000, false_positive_rate=0.01
    ):
        """
        初始化布隆过滤器
        :param items: 初始字符串列表
        :param expected_items: 预估元素数量
        :param false_positive_rate: 目标误判率
        """
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate

        self.size = self._optimal_size(expected_items, false_positive_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_items)

        self.bit_array = bitarray.bitarray(self.size)
        self.bit_array.setall(0)

        for item in items:
            self.add(item)

    @staticmethod
    def _optimal_size(n, p):
        """根据 n 和 p 计算位图大小 m"""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)

    @staticmethod
    def _optimal_hash_count(m, n):
        """根据位图大小 m 和元素个数 n 计算哈希函数个数 k"""
        k = (m / n) * math.log(2)
        return max(1, int(k))

    def _hashes(self, item: str):
        """多次哈希，得到多个位图索引"""
        hashes = []
        for i in range(self.hash_count):
            digest = hashlib.md5(f"{item}_{i}".encode()).hexdigest()
            hash_val = int(digest, 16) % self.size
            hashes.append(hash_val)
        return hashes

    def add(self, item: str):
        """添加元素"""
        for hash_val in self._hashes(item):
            self.bit_array[hash_val] = 1

    def __contains__(self, item: str) -> bool:
        """检查元素是否可能存在"""
        return all(self.bit_array[hash_val] for hash_val in self._hashes(item))

    def save(self, filename: str):
        """保存到文件"""
        with open(filename, "wb") as f:
            pickle.dump(
                {
                    "expected_items": self.expected_items,
                    "false_positive_rate": self.false_positive_rate,
                    "size": self.size,
                    "hash_count": self.hash_count,
                    "bit_array": self.bit_array,
                },
                f,
            )

    @classmethod
    def load(cls, filename: str):
        """从文件加载（不存在则返回 None）"""
        if not os.path.exists(filename):
            return None

        with open(filename, "rb") as f:
            data = pickle.load(f)

        bloom = cls(
            expected_items=data["expected_items"],
            false_positive_rate=data["false_positive_rate"],
        )
        bloom.size = data["size"]
        bloom.hash_count = data["hash_count"]
        bloom.bit_array = data["bit_array"]
        return bloom

    @classmethod
    def load_or_create(
        cls,
        filename: str,
        expected_items=1000,
        false_positive_rate=0.01,
        auto_save_on_create=False,
    ):
        """
        加载 BloomFilter，如果文件不存在则创建新实例
        :param auto_save_on_create: 新建时是否自动保存
        """
        bloom = cls.load(filename)
        if bloom is None:
            bloom = cls(
                expected_items=expected_items, false_positive_rate=false_positive_rate
            )
            if auto_save_on_create:
                bloom.save(filename)
        return bloom
