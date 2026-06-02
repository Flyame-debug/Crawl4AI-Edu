"""
link_utils.py —— 链接发现与 URL 去重模块

提供两个核心能力：
1. extract_links: 从 HTML 中按白名单规则智能提取链接
2. BloomFilterURLQueue: 基于布隆过滤器的内存版 URL 去重队列

独立于 sandbox/fetcher/ 模块，不依赖 Django、Celery、数据库。
"""

import logging
import re
import urllib.parse
from typing import List

from pybloom_live import ScalableBloomFilter  # NEW_DEP: pybloom_live
from scrapy.http import HtmlResponse  # NEW_DEP: scrapy
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor  # NEW_DEP: scrapy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 顶层函数（共 3 个）
# ---------------------------------------------------------------------------


def extract_links(
    html: str,
    base_url: str,
    allowed_domains: List[str],
    white_list_patterns: List[str],
) -> List[str]:
    """从 HTML 中提取符合白名单规则的绝对链接。

    Args:
        html: 页面 HTML 字符串。
        base_url: 当前页面的完整 URL，用于相对路径拼接。
        allowed_domains: 域名白名单，如 ['.tsinghua.edu.cn', '.pku.edu.cn']，
            支持前导通配符（.example.com 匹配所有子域名）。
        white_list_patterns: URL 路径正则白名单，如 ['/teacher/.*', '/faculty/.*']。
            若包含纯字符串（不含正则元字符），将自动转为 .*pattern.* 形式。

    Returns:
        去重后的绝对 URL 列表（同一页面内去重，不含 javascript/mailto 等无效链接）。
        解析失败或 html 为空时返回空列表。
    """
    if not html or not html.strip():
        logger.warning("extract_links: html 为空，返回空列表")
        return []

    # 修复 / 规范化 base_url
    parsed_base = urllib.parse.urlparse(base_url)
    if not parsed_base.scheme or not parsed_base.netloc:
        # 尝试添加默认 scheme
        fixed = urllib.parse.urlparse(f"http://{base_url}")
        if fixed.scheme and fixed.netloc:
            base_url = f"http://{base_url}"
        else:
            logger.warning("extract_links: base_url 格式无效 → %s", base_url)
            return []

    # 将纯字符串模式转为正则
    normalized_patterns = _normalize_patterns(white_list_patterns)

    # 规范化域名：去除前导 "."，适配 Scrapy 的域名匹配逻辑
    # Scrapy 内部用 host.endswith(f".{d}") 匹配子域名，"example.edu" 即可覆盖
    # 所有子域；".example.edu" 反而会产生 "..example.edu" 的双点问题。
    normalized_domains = tuple(
        d[1:] if d.startswith(".") else d for d in allowed_domains
    ) if allowed_domains else ()

    # 构建提取器
    extractor = LxmlLinkExtractor(
        allow=tuple(normalized_patterns) if normalized_patterns else (),
        allow_domains=normalized_domains,
        unique=True,
        strip=True,
    )

    # 构建 Scrapy Response 对象（extract_links 需要 Response，不能直接传字符串）
    response = HtmlResponse(url=base_url, body=html, encoding="utf-8")

    try:
        links = extractor.extract_links(response)
    except Exception:
        logger.exception("extract_links: LxmlLinkExtractor 解析失败")
        return []

    result: List[str] = []
    for link in links:
        # urljoin 将相对路径转为绝对 URL（处理 extractor 未完全规范化的链接）
        absolute = urllib.parse.urljoin(base_url, link.url)
        if _is_valid_url(absolute):
            result.append(absolute)

    return result


def _normalize_patterns(patterns: List[str]) -> List[str]:
    """将纯字符串前缀模式自动转为正则。

    '/teacher/' → '.*/teacher/.*'
    '/teacher/.*' → 保持不变（已含正则元字符）
    """
    normalized: List[str] = []
    for pattern in patterns:
        if re.search(r"[.*+?\[\](){}^$|\\]", pattern):
            # 已包含正则元字符，直接使用
            normalized.append(pattern)
        else:
            # 纯字符串，转为包含匹配
            normalized.append(".*" + re.escape(pattern) + ".*")
    return normalized


def _is_valid_url(url: str) -> bool:
    """过滤无效链接：javascript、mailto、tel、纯锚点、非 http(s) 协议。"""
    if not url:
        return False
    lowered = url.strip().lower()
    # 过滤伪协议
    if lowered.startswith(("javascript:", "mailto:", "tel:")):
        return False
    # 过滤纯锚点
    if lowered.startswith("#"):
        return False
    # 过滤非 http(s) 协议（已转为绝对 URL 后才有 scheme）
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return False
    return True


# ---------------------------------------------------------------------------
# 布隆过滤器 URL 去重队列
# ---------------------------------------------------------------------------


class BloomFilterURLQueue:
    """基于可扩容布隆过滤器的 URL 去重队列。

    使用 pybloom_live.ScalableBloomFilter 自动扩容，避免容量预估不准。
    布隆过滤器存在误判（False Positive），在 URL 去重场景中可接受。

    Examples:
        >>> queue = BloomFilterURLQueue(capacity=1000, error_rate=0.001)
        >>> queue.add("https://example.com/page1")
        True
        >>> queue.add("https://example.com/page1")
        False
        >>> queue.contains("https://example.com/page1")
        True
        >>> queue.size()
        1
    """

    def __init__(self, capacity: int = 100000, error_rate: float = 0.001) -> None:
        """初始化布隆过滤器。

        Args:
            capacity: 预期最大 URL 数量，用于初始容量分配。
            error_rate: 目标误判率，越小越精确但消耗更多内存。
        """
        self._bf = ScalableBloomFilter(
            initial_capacity=capacity,
            error_rate=error_rate,
        )
        self._capacity = capacity
        self._error_rate = error_rate

    def add(self, url: str) -> bool:
        """添加 URL 到过滤器。

        Args:
            url: 待添加的 URL 字符串。

        Returns:
            True 表示新 URL（之前不存在），False 表示可能已存在。
            时间复杂度 O(k)，k 为哈希函数个数。
        """
        if url in self._bf:
            return False
        self._bf.add(url)
        return True

    def contains(self, url: str) -> bool:
        """检查 URL 是否已存在。

        Args:
            url: 待检查的 URL 字符串。

        Returns:
            True 表示可能已存在（含误判），False 表示一定不存在。
        """
        return url in self._bf

    def size(self) -> int:
        """返回当前已添加的不同 URL 数量（近似值）。"""
        return self._bf.count

    def clear(self) -> None:
        """清空布隆过滤器，重置到初始状态。"""
        self._bf = ScalableBloomFilter(
            initial_capacity=self._capacity,
            error_rate=self._error_rate,
        )


# ---------------------------------------------------------------------------
# 测试代码
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    passed = 0
    failed = 0

    def check(condition: bool, label: str) -> None:
        global passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {label}")
        else:
            failed += 1
            print(f"  [FAIL] {label}")

    # ---- 3.1 extract_links 测试 ----
    print("=" * 60)
    print("3.1 测试 extract_links")
    print("=" * 60)

    mock_html = """
    <html><body>
        <h1>教师列表</h1>
        <a href="/teacher/zhangsan.html">张三</a>
        <a href="/teacher/lisi?page=1">李四</a>
        <a href="https://www.example.edu/teacher/wangwu">王五</a>
        <a href="/student/001">学生A</a>
        <a href="javascript:void(0)">无效链接</a>
        <a href="mailto:admin@example.edu">邮箱</a>
        <a href="tel:+8613800000000">电话</a>
        <a href="#footer">页脚锚点</a>
        <a href="ftp://files.example.edu/data.zip">FTP链接</a>
    </body></html>
    """

    base_url = "https://www.example.edu"
    allowed_domains = [".example.edu"]
    white_list_patterns = ["/teacher/.*"]

    links = extract_links(mock_html, base_url, allowed_domains, white_list_patterns)

    print(f"  提取到的链接数: {len(links)}")
    for link in links:
        print(f"    → {link}")

    check(len(links) == 3, f"应提取 3 个链接，实际 {len(links)} 个")
    check(
        all("/teacher/" in link for link in links),
        "所有链接应包含 /teacher/",
    )
    check(
        all(link.startswith("https://") for link in links),
        "所有链接应为绝对 URL（https 协议）",
    )

    # 测试相对路径转绝对路径
    has_zhangsan = any("zhangsan" in link for link in links)
    check(has_zhangsan, "应包含相对路径转换后的 /teacher/zhangsan.html")

    # 测试空 HTML
    empty_result = extract_links("", base_url, allowed_domains, white_list_patterns)
    check(len(empty_result) == 0, "空 HTML 应返回空列表")

    # 测试提取到的链接已正确过滤无效协议
    all_valid = all(
        not link.startswith(("javascript:", "mailto:", "tel:", "ftp:", "#"))
        for link in links
    )
    check(all_valid, "所有提取的链接不应包含 javascript/mailto/tel/ftp/锚点")

    # 测试纯字符串前缀自动转正则（扩展需求）
    print("\n--- 扩展：字符串前缀自动转正则 ---")
    prefix_links = extract_links(
        mock_html, base_url, allowed_domains, ["/student/"]  # 纯字符串，非正则
    )
    print(f"  使用纯字符串 '/student/' 模式提取到的链接数: {len(prefix_links)}")
    for link in prefix_links:
        print(f"    → {link}")
    check(len(prefix_links) == 1, "纯字符串 '/student/' 应匹配到 1 个链接")
    check(
        "/student/001" in prefix_links[0] if prefix_links else False,
        "应匹配到 /student/001",
    )

    # ---- 3.2 布隆过滤器测试 ----
    print("\n" + "=" * 60)
    print("3.2 测试 BloomFilterURLQueue")
    print("=" * 60)

    bf = BloomFilterURLQueue(capacity=100, error_rate=0.001)
    test_urls = [
        "https://www.example.edu/teacher/001",
        "https://www.example.edu/teacher/002",
        "https://www.example.edu/teacher/003",
        "https://www.example.edu/teacher/004",
        "https://www.example.edu/teacher/005",
    ]

    print("  添加 5 个不同 URL ...")
    for i, url in enumerate(test_urls, 1):
        result = bf.add(url)
        print(f"    add({url!r}) → {result}")
        check(result is True, f"第 {i} 次 add 应返回 True（新 URL）")

    # 重复添加第一个
    print("  重复添加第一个 URL ...")
    dup_result = bf.add(test_urls[0])
    print(f"    add({test_urls[0]!r}) → {dup_result}")
    check(dup_result is False, "重复添加应返回 False")

    # contains 检查
    print("  contains 检查 ...")
    check(bf.contains(test_urls[0]) is True, "contains 应找到已存在的 URL")
    check(
        bf.contains("https://www.example.edu/teacher/999") is False,
        "contains 应返回 False（不存在的 URL）",
    )

    # size 检查
    print(f"  size() = {bf.size()}")
    check(bf.size() == 5, f"size 应为 5，实际为 {bf.size()}")

    # clear 测试
    print("  测试 clear() ...")
    bf.clear()
    check(bf.size() == 0, f"clear 后 size 应为 0，实际为 {bf.size()}")
    check(
        bf.contains(test_urls[0]) is False,
        "clear 后 contains 应返回 False",
    )

    # ---- 3.3 集成测试 ----
    print("\n" + "=" * 60)
    print("3.3 集成场景测试")
    print("=" * 60)

    # 使用两段模拟 HTML，模拟从不同页面提取链接并去重
    mock_html_2 = """
    <html><body>
        <a href="/teacher/zhangsan.html">张三</a>
        <a href="/teacher/lisi">李四</a>
        <a href="/teacher/zhaoliu">赵六</a>
    </body></html>
    """

    bf2 = BloomFilterURLQueue(capacity=100, error_rate=0.001)
    new_count = 0

    # 第一页
    links_page1 = extract_links(
        mock_html, base_url, allowed_domains, white_list_patterns
    )
    for url in links_page1:
        if bf2.add(url):
            new_count += 1
    print(f"  第 1 页提取 {len(links_page1)} 个链接，新增 {new_count} 个")

    # 第二页（部分重叠）
    links_page2_count_before = new_count
    links_page2 = extract_links(
        mock_html_2, base_url, allowed_domains, white_list_patterns
    )
    for url in links_page2:
        if bf2.add(url):
            new_count += 1
    print(f"  第 2 页提取 {len(links_page2)} 个链接，累计新增 {new_count} 个")
    print(f"  第 2 页实际新增 {new_count - links_page2_count_before} 个")
    print(f"  布隆过滤器 size = {bf2.size()}")

    # 第 1 页 3 个 + 第 2 页 2 个新链接（/teacher/lisi ≠ /teacher/lisi?page=1，zhangsan 重复）
    check(bf2.size() == 5, f"去重后应有 5 个唯一 URL，实际 {bf2.size()}")
    check(
        new_count == 5,
        f"累计新增应为 5（含第 2 页的 2 个新链接），实际 {new_count}",
    )

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    if failed == 0:
        print("所有测试通过 ✓")
    else:
        print(f"有 {failed} 个测试未通过 ✗")
    print("=" * 60)
