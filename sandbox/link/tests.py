"""
tests.py —— sandbox.link 模块独立测试脚本。

覆盖场景：
- extract_links 链接提取（白名单、域名过滤、无效链接过滤、纯字符串转正则）
- MemoryBloomFilter 增删查
- RedisBloomFilter 增删查（Redis 不可用时自动跳过）
- 线程安全性验证
- 集成场景：多页提取 + 去重

用法:
    python sandbox/link/tests.py                 # 内存版全部测试
    python sandbox/link/tests.py --backend redis  # Redis 版（需本地 Redis）
"""

import argparse
import logging
import os
import sys
import threading
import unittest
from typing import List

# 确保 sandbox/ 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from link.bloom_filter import (
    MemoryBloomFilter,
    RedisBloomFilter,
    create_bloom_filter,
)
from link.extractor import extract_links

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

MOCK_HTML = """
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

MOCK_HTML_2 = """
<html><body>
    <a href="/teacher/zhangsan.html">张三</a>
    <a href="/teacher/lisi">李四</a>
    <a href="/teacher/zhaoliu">赵六</a>
</body></html>
"""

BASE_URL = "https://www.example.edu"
ALLOWED_DOMAINS = [".example.edu"]
WHITE_LIST_PATTERNS = ["/teacher/.*"]

TEST_URLS = [
    "https://www.example.edu/teacher/001",
    "https://www.example.edu/teacher/002",
    "https://www.example.edu/teacher/003",
    "https://www.example.edu/teacher/004",
    "https://www.example.edu/teacher/005",
]


def _redis_available() -> bool:
    """检测本地 Redis 是否可用。"""
    try:
        import redis as _redis
        r = _redis.Redis(host="localhost", port=6379, socket_connect_timeout=1.0)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------


class ExtractLinksTest(unittest.TestCase):
    """extract_links 链接提取测试。"""

    def test_extract_teacher_links(self):
        """测试白名单提取：只保留 /teacher/.* 的链接。"""
        links = extract_links(MOCK_HTML, BASE_URL, ALLOWED_DOMAINS, WHITE_LIST_PATTERNS)
        self.assertEqual(len(links), 3, f"应提取 3 个链接，实际 {len(links)} 个")
        for link in links:
            self.assertIn("/teacher/", link)
            self.assertTrue(link.startswith("https://"))
        # 验证相对路径已转为绝对路径
        has_zhangsan = any("zhangsan" in link for link in links)
        self.assertTrue(has_zhangsan, "应包含相对路径转换的 /teacher/zhangsan.html")

    def test_filters_invalid_urls(self):
        """测试无效链接被正确过滤。"""
        links = extract_links(MOCK_HTML, BASE_URL, ALLOWED_DOMAINS, WHITE_LIST_PATTERNS)
        for link in links:
            self.assertFalse(
                link.startswith(("javascript:", "mailto:", "tel:", "ftp:", "#")),
                f"不应出现无效链接: {link}",
            )

    def test_empty_html(self):
        """测试空 HTML 返回空列表。"""
        result = extract_links("", BASE_URL, ALLOWED_DOMAINS, WHITE_LIST_PATTERNS)
        self.assertEqual(len(result), 0)

    def test_whitespace_html(self):
        """测试纯空白 HTML 返回空列表。"""
        result = extract_links("   \n  ", BASE_URL, ALLOWED_DOMAINS, WHITE_LIST_PATTERNS)
        self.assertEqual(len(result), 0)

    def test_plain_string_auto_regex(self):
        """测试纯字符串白名单自动转为正则（扩展需求）。"""
        links = extract_links(MOCK_HTML, BASE_URL, ALLOWED_DOMAINS, ["/student/"])
        self.assertEqual(len(links), 1, f"纯字符串 '/student/' 应匹配 1 个，实际 {len(links)}")
        if links:
            self.assertIn("/student/001", links[0])


class MemoryBloomFilterTest(unittest.TestCase):
    """MemoryBloomFilter 单元测试。"""

    def setUp(self):
        self.bf = MemoryBloomFilter(capacity=100, error_rate=0.001)

    def test_add_new_urls(self):
        """测试添加新 URL 返回 True。"""
        for url in TEST_URLS:
            self.assertTrue(self.bf.add(url), f"add({url}) 应返回 True")

    def test_add_duplicate(self):
        """测试重复添加返回 False。"""
        self.bf.add(TEST_URLS[0])
        self.assertFalse(self.bf.add(TEST_URLS[0]), "重复添加应返回 False")

    def test_contains(self):
        """测试 contains 检查。"""
        self.bf.add(TEST_URLS[0])
        self.assertTrue(self.bf.contains(TEST_URLS[0]))
        self.assertFalse(self.bf.contains("https://www.example.edu/teacher/999"))

    def test_size(self):
        """测试 size 计数正确。"""
        for url in TEST_URLS:
            self.bf.add(url)
        self.assertEqual(self.bf.size(), 5)

    def test_clear(self):
        """测试 clear 清空。"""
        for url in TEST_URLS:
            self.bf.add(url)
        self.bf.clear()
        self.assertEqual(self.bf.size(), 0)
        self.assertFalse(self.bf.contains(TEST_URLS[0]))


class MemoryBloomFilterThreadSafetyTest(unittest.TestCase):
    """MemoryBloomFilter 线程安全性测试。"""

    def test_concurrent_adds(self):
        """测试多线程并发添加无竞争条件。"""
        bf = MemoryBloomFilter(capacity=10000, error_rate=0.001)
        errors = []
        results: List[bool] = []

        def worker(urls):
            for url in urls:
                try:
                    results.append(bf.add(url))
                except Exception as e:
                    errors.append(e)

        # 生成 500 个唯一 URL，50 个线程同时添加
        urls_per_thread = [
            [f"https://example.edu/page/{i}_{t}" for i in range(10)]
            for t in range(50)
        ]
        threads = []
        for subset in urls_per_thread:
            t = threading.Thread(target=worker, args=(subset,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"并发添加出现异常: {errors}")
        # 所有 URL 唯一，应全部为 True
        total_urls = sum(len(s) for s in urls_per_thread)
        true_count = sum(1 for r in results if r)
        self.assertEqual(
            true_count, total_urls,
            f"应为 {total_urls} 个 True，实际 {true_count} 个",
        )
        self.assertEqual(bf.size(), total_urls)


class RedisBloomFilterTest(unittest.TestCase):
    """RedisBloomFilter 集成测试（Redis 不可用时跳过）。"""

    @classmethod
    def setUpClass(cls):
        if not _redis_available():
            raise unittest.SkipTest("Redis 不可用，跳过 RedisBloomFilter 测试")

    def setUp(self):
        self.bf = RedisBloomFilter(
            capacity=1000,
            error_rate=0.001,
            key_prefix="crawl4ai:test",
        )
        self.bf.clear()

    def tearDown(self):
        self.bf.clear()
        try:
            self.bf.close()
        except Exception:
            pass

    def test_add_new_urls(self):
        """测试 Redis 版添加新 URL 返回 True。"""
        for url in TEST_URLS:
            self.assertTrue(self.bf.add(url), f"add({url}) 应返回 True")

    def test_add_duplicate(self):
        """测试 Redis 版重复添加返回 False。"""
        self.bf.add(TEST_URLS[0])
        self.assertFalse(self.bf.add(TEST_URLS[0]), "重复添加应返回 False")

    def test_contains(self):
        """测试 Redis 版 contains 检查。"""
        self.bf.add(TEST_URLS[0])
        self.assertTrue(self.bf.contains(TEST_URLS[0]))
        self.assertFalse(self.bf.contains("https://www.example.edu/teacher/999"))

    def test_size(self):
        """测试 Redis 版 size 计数正确。"""
        for url in TEST_URLS:
            self.bf.add(url)
        self.assertEqual(self.bf.size(), 5)

    def test_clear(self):
        """测试 Redis 版 clear 清空。"""
        for url in TEST_URLS:
            self.bf.add(url)
        self.bf.clear()
        self.assertEqual(self.bf.size(), 0)
        self.assertFalse(self.bf.contains(TEST_URLS[0]))

    def test_capacity_estimation(self):
        """测试 10 万容量、0.1% 误判率下的参数合理性。"""
        bf = RedisBloomFilter(
            capacity=100000,
            error_rate=0.001,
            key_prefix="crawl4ai:test:large",
        )
        self.assertGreater(bf._m, 100000, "m 应大于容量")
        self.assertGreater(bf._k, 1, "k 应大于 1")
        bf.clear()
        bf.close()


class FactoryTest(unittest.TestCase):
    """create_bloom_filter 工厂函数测试。"""

    def test_create_memory(self):
        bf = create_bloom_filter("memory", capacity=500, error_rate=0.01)
        self.assertIsInstance(bf, MemoryBloomFilter)
        self.assertTrue(bf.add("https://example.com/test"))
        self.assertEqual(bf.size(), 1)

    def test_create_redis_if_available(self):
        if not _redis_available():
            self.skipTest("Redis 不可用")
        bf = create_bloom_filter(
            "redis",
            capacity=500,
            error_rate=0.01,
            key_prefix="crawl4ai:test:factory",
        )
        self.assertIsInstance(bf, RedisBloomFilter)
        bf.clear()
        bf.close()

    def test_create_invalid_backend(self):
        with self.assertRaises(ValueError):
            create_bloom_filter("invalid_backend")


class IntegrationTest(unittest.TestCase):
    """集成场景测试：多页提取 + 去重。"""

    def setUp(self):
        self.bf = MemoryBloomFilter(capacity=100, error_rate=0.001)

    def test_multi_page_dedup(self):
        """测试两页提取后的全局去重结果。"""
        new_count = 0

        links_page1 = extract_links(
            MOCK_HTML, BASE_URL, ALLOWED_DOMAINS, WHITE_LIST_PATTERNS
        )
        for url in links_page1:
            if self.bf.add(url):
                new_count += 1
        self.assertEqual(len(links_page1), 3)

        before_page2 = new_count
        links_page2 = extract_links(
            MOCK_HTML_2, BASE_URL, ALLOWED_DOMAINS, WHITE_LIST_PATTERNS
        )
        for url in links_page2:
            if self.bf.add(url):
                new_count += 1
        self.assertEqual(len(links_page2), 3)

        # 第 1 页 3 个 + 第 2 页 2 个新链接
        # (/teacher/lisi ≠ /teacher/lisi?page=1，zhangsan 重复）
        self.assertEqual(self.bf.size(), 5)
        self.assertEqual(new_count, 5)
        self.assertEqual(new_count - before_page2, 2)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="sandbox.link 模块测试")
    parser.add_argument(
        "--backend",
        choices=["memory", "redis"],
        default="memory",
        help="布隆过滤器后端（默认 memory）",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 选择要运行的测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 始终运行链接提取测试
    suite.addTests(loader.loadTestsFromTestCase(ExtractLinksTest))

    # 始终运行内存版测试
    suite.addTests(loader.loadTestsFromTestCase(MemoryBloomFilterTest))
    suite.addTests(loader.loadTestsFromTestCase(MemoryBloomFilterThreadSafetyTest))

    # 始终运行工厂函数测试
    suite.addTests(loader.loadTestsFromTestCase(FactoryTest))

    # 始终运行集成测试
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTest))

    # 仅 --backend=redis 时运行 Redis 测试
    if args.backend == "redis":
        suite.addTests(loader.loadTestsFromTestCase(RedisBloomFilterTest))
        print("已启用 Redis 后端测试")
    else:
        print("运行内存版测试（使用 --backend=redis 切换至 Redis 版）")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 汇总
    print("\n" + "=" * 60)
    print(f"测试结果: {result.testsRun - len(result.errors) - len(result.failures)} 通过, "
          f"{len(result.failures)} 失败, {len(result.errors)} 错误, "
          f"{len(result.skipped)} 跳过")
    if result.wasSuccessful():
        print("所有测试通过 ✓")
    else:
        print("存在未通过的测试 ✗")
    print("=" * 60)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
