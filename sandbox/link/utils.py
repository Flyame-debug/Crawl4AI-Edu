"""
utils.py —— 链接发现与去重模块的辅助纯函数。

提供 URL 有效性检查、域名规范化和白名单模式自动转正则等工具函数，
不依赖任何 sandbox/ 内部模块。
"""

import re
import urllib.parse
from typing import List


def normalize_domain(domain: str) -> str:
    """规范化域名：去除前导 "." 以适配 Scrapy 域名匹配逻辑。

    Scrapy 内部使用 host.endswith(f".{d}") 匹配子域名，若传入 ".example.edu"
    会产生 "..example.edu" 双点问题。去除前导 "." 后 "example.edu" 即可
    覆盖所有子域名和裸域名。

    Args:
        domain: 原始域名字符串，如 ".tsinghua.edu.cn" 或 "example.com"。

    Returns:
        去除前导 "." 后的域名字符串。

    Examples:
        >>> normalize_domain(".example.edu")
        'example.edu'
        >>> normalize_domain("example.com")
        'example.com'
    """
    return domain[1:] if domain.startswith(".") else domain


def is_valid_url(url: str) -> bool:
    """检查 URL 是否有效：过滤伪协议、纯锚点、非 http(s) 协议。

    Args:
        url: 待检查的 URL 字符串（应为已规范化的绝对 URL）。

    Returns:
        True 表示该 URL 是有效的 http/https 链接。

    Examples:
        >>> is_valid_url("https://example.com/page")
        True
        >>> is_valid_url("javascript:void(0)")
        False
        >>> is_valid_url("mailto:admin@example.com")
        False
    """
    if not url:
        return False
    lowered = url.strip().lower()
    if lowered.startswith(("javascript:", "mailto:", "tel:")):
        return False
    if lowered.startswith("#"):
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return False
    return True


def normalize_patterns(patterns: List[str]) -> List[str]:
    """将纯字符串白名单模式自动转为包含匹配的正则。

    若 pattern 已包含正则元字符（如 .*+?[](){}^$|\\），保持原样；
    否则视为纯字符串前缀，自动转为 .*pattern.* 形式。

    Args:
        patterns: 原始白名单模式列表。

    Returns:
        规范化后的正则模式列表。

    Examples:
        >>> normalize_patterns(["/teacher/.*"])
        ['/teacher/.*']
        >>> normalize_patterns(["/teacher/"])
        ['.*/teacher/.*']
    """
    normalized: List[str] = []
    for pattern in patterns:
        if re.search(r"[.*+?\[\](){}^$|\\]", pattern):
            normalized.append(pattern)
        else:
            normalized.append(".*" + re.escape(pattern) + ".*")
    return normalized
