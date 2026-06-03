"""
sandbox.link —— 链接发现与 URL 去重模块。

提供两个核心公开接口：
- extract_links: 从 HTML 中智能提取符合白名单规则的链接
- create_bloom_filter: 创建可插拔布隆过滤器实例（memory / redis）

使用方式:
    from sandbox.link import extract_links, create_bloom_filter

    links = extract_links(html, base_url, [".example.edu"], ["/teacher/.*"])

    bf = create_bloom_filter("memory", capacity=100000)
    bf.add("https://example.com/page1")

子模块:
    extractor.py     —— 链接提取（extract_links）
    bloom_filter.py  —— 布隆过滤器后端（Memory / Redis）
    utils.py         —— 辅助纯函数
    tests.py         —— 独立测试脚本
"""

from .bloom_filter import create_bloom_filter, URLBloomFilterBackend
from .extractor import extract_links

__all__ = [
    "extract_links",
    "create_bloom_filter",
    "URLBloomFilterBackend",
]
