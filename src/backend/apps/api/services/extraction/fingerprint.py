"""
文件名: fingerprint.py
作用: 计算页面 DOM 结构指纹，用于模板匹配和聚类
主要功能:
    1. 从原始 HTML 提取前两层 DOM 标签序列
    2. 使用 simhash 计算 64 位哈希指纹
    3. 计算两个指纹之间的海明距离
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger('apps')

# simhash 指纹位数
SIMHASH_BITS = 64

# DOM 标签序列提取的最大深度（前 N 层）
# 深度设为 4 以确保不同页面结构的指纹能有效区分
MAX_TAG_DEPTH = 4


def compute_fingerprint(raw_html: str) -> Optional[int]:
    """
    作用: 从原始 HTML 计算 DOM 结构 simhash 指纹

    处理流程:
        1. BeautifulSoup 解析 HTML
        2. 提取前两层 DOM 标签序列（如 html,body,div,p）
        3. 使用 simhash 计算指纹

    参数:
        raw_html: 原始 HTML 字符串

    返回:
        整数指纹值，失败时返回 None
    """
    if not raw_html or not raw_html.strip():
        logger.warning('compute_fingerprint: raw_html 为空')
        return None

    try:
        soup = BeautifulSoup(raw_html, 'html.parser')
        tag_sequence = _extract_tag_sequence(soup, max_depth=MAX_TAG_DEPTH)
        tag_text = ' '.join(tag_sequence)

        if not tag_text.strip():
            logger.warning('compute_fingerprint: 标签序列为空')
            return None

        from simhash import Simhash
        fingerprint = Simhash(tag_text, f=SIMHASH_BITS)
        return fingerprint.value

    except ImportError:
        logger.error('compute_fingerprint: simhash 库未安装，请执行 pip install simhash')
        return None
    except Exception as e:
        logger.error(f'compute_fingerprint 异常: {e}')
        return None


def _extract_tag_sequence(soup: BeautifulSoup, max_depth: int = 2) -> list:
    """
    作用: 从 BeautifulSoup 解析树中提取前 max_depth 层的标签序列

    使用 BFS 遍历，按层级截取标签名列表。
    """
    tag_names = []
    depth_sep = []  # 标记层级分隔

    # BFS 遍历
    queue = [(soup, 0)]
    while queue and len(tag_names) < 500:  # 防止无限循环
        node, depth = queue.pop(0)

        if depth > max_depth:
            break

        if hasattr(node, 'name') and node.name:
            tag_names.append(node.name)
            if depth < max_depth and hasattr(node, 'children'):
                for child in node.children:
                    if hasattr(child, 'name') and child.name:
                        queue.append((child, depth + 1))

    return tag_names


def hamming_distance(fp1: int, fp2: int) -> int:
    """
    作用: 计算两个 simhash 指纹之间的海明距离
    """
    x = (fp1 ^ fp2) & ((1 << SIMHASH_BITS) - 1)
    distance = 0
    while x:
        distance += 1
        x &= x - 1
    return distance


def is_similar(fp1: int, fp2: int, threshold: int = 8) -> bool:
    """
    作用: 判断两个指纹是否相似（海明距离小于阈值）

    参数:
        fp1, fp2: 两个 simhash 指纹值
        threshold: 海明距离阈值，默认 8（约 87.5% 相似度）
    """
    return hamming_distance(fp1, fp2) <= threshold
