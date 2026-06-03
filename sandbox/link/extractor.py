"""
extractor.py —— 链接提取模块。

提供 extract_links 函数，基于 scrapy.LxmlLinkExtractor 从 HTML 中智能提取
符合域名和路径白名单规则的链接。独立于 sandbox/fetcher/ 模块。
"""

import logging
import urllib.parse
from typing import List

from scrapy.http import HtmlResponse  # NEW_DEP: scrapy
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor  # NEW_DEP: scrapy

from .utils import is_valid_url, normalize_domain, normalize_patterns

logger = logging.getLogger(__name__)


def extract_links(
    html: str,
    base_url: str,
    allowed_domains: List[str],
    white_list_patterns: List[str],
) -> List[str]:
    """从 HTML 中提取符合白名单规则的绝对链接。

    使用 scrapy.LxmlLinkExtractor 进行链接提取，支持域名白名单（前导通配符
    ".example.com" 自动适配）和路径正则白名单。相对路径通过 urljoin 转为绝对 URL。
    自动过滤 javascript:、mailto:、tel:、纯锚点及非 http(s) 协议链接。

    Args:
        html: 页面 HTML 字符串。
        base_url: 当前页面的完整 URL，用于相对路径拼接。
        allowed_domains: 域名白名单列表，如 ['.tsinghua.edu.cn', '.pku.edu.cn']。
            支持前导通配符 ".example.com" 匹配所有子域名及裸域名。
        white_list_patterns: URL 路径正则白名单，如 ['/teacher/.*', '/faculty/.*']。
            纯字符串（不含正则元字符）将自动转为 .*pattern.* 包含匹配。

    Returns:
        去重后的绝对 URL 列表（同一页面内去重，不含无效链接）。
        html 为空或解析失败时返回空列表。

    Examples:
        >>> html = '<a href="/teacher/zhangsan.html">Teacher</a>'
        >>> extract_links(html, "https://www.example.edu",
        ...               [".example.edu"], ["/teacher/.*"])
        ['https://www.example.edu/teacher/zhangsan.html']
    """
    if not html or not html.strip():
        logger.warning("extract_links: html 为空，返回空列表")
        return []

    # 修复 / 规范化 base_url
    parsed_base = urllib.parse.urlparse(base_url)
    if not parsed_base.scheme or not parsed_base.netloc:
        fixed = urllib.parse.urlparse(f"http://{base_url}")
        if fixed.scheme and fixed.netloc:
            base_url = f"http://{base_url}"
        else:
            logger.warning("extract_links: base_url 格式无效 → %s", base_url)
            return []

    # 规范化白名单模式与域名
    normalized_patterns = normalize_patterns(white_list_patterns)
    normalized_domains = tuple(
        normalize_domain(d) for d in allowed_domains
    ) if allowed_domains else ()

    # 构建 Scrapy 链接提取器
    extractor = LxmlLinkExtractor(
        allow=tuple(normalized_patterns) if normalized_patterns else (),
        allow_domains=normalized_domains,
        unique=True,
        strip=True,
    )

    # 构建 Response 对象（extract_links 需要 Response，不能直接传字符串）
    response = HtmlResponse(url=base_url, body=html, encoding="utf-8")

    try:
        links = extractor.extract_links(response)
    except Exception:
        logger.exception("extract_links: LxmlLinkExtractor 解析失败")
        return []

    result: List[str] = []
    for link in links:
        absolute = urllib.parse.urljoin(base_url, link.url)
        if is_valid_url(absolute):
            result.append(absolute)

    return result
