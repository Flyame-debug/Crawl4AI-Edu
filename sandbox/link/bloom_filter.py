"""
bloom_filter.py —— 可插拔布隆过滤器后端。

提供抽象基类 URLBloomFilterBackend 及两个具体实现：
- MemoryBloomFilter: 基于 pybloom_live.ScalableBloomFilter 的内存版，线程安全
- RedisBloomFilter: 基于 Redis Bitmap + 多哈希函数的手工实现，支持多 Worker 共享

工厂函数 create_bloom_filter() 根据 backend 参数创建对应实例。
"""

import hashlib
import logging
import math
import os
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import redis  # NEW_DEP: redis
from pybloom_live import ScalableBloomFilter  # NEW_DEP: pybloom_live

logger = logging.getLogger(__name__)

# 默认 Redis 连接地址
DEFAULT_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------


class URLBloomFilterBackend(ABC):
    """布隆过滤器后端抽象基类。

    定义 URL 去重所需的统一接口，所有后端（内存版、Redis 版等）必须实现
    以下四个方法。调用方无需关心底层实现细节。

    Examples:
        >>> bf = MemoryBloomFilter(capacity=1000, error_rate=0.001)
        >>> bf.add("https://example.com")  # True
        >>> bf.contains("https://example.com")  # True
    """

    @abstractmethod
    def add(self, url: str) -> bool:
        """添加 URL，返回 True 表示新 URL，False 表示可能已存在。"""
        ...

    @abstractmethod
    def contains(self, url: str) -> bool:
        """检查 URL 是否已存在，True 表示可能存在（含误判），False 表示一定不存在。"""
        ...

    @abstractmethod
    def size(self) -> int:
        """返回当前已添加的不同 URL 数量（近似值）。"""
        ...

    @abstractmethod
    def clear(self) -> None:
        """清空过滤器，重置到初始状态。"""
        ...


# ---------------------------------------------------------------------------
# 内存版实现
# ---------------------------------------------------------------------------


class MemoryBloomFilter(URLBloomFilterBackend):
    """基于 pybloom_live.ScalableBloomFilter 的内存版布隆过滤器。

    线程安全：使用 threading.Lock 保护 add 和 contains 操作。
    仅适用于单进程开发/测试场景，多 Worker（多进程）下不共享状态。

    Examples:
        >>> bf = MemoryBloomFilter(capacity=100000, error_rate=0.001)
        >>> bf.add("https://example.com/page1")
        True
        >>> bf.add("https://example.com/page1")
        False
        >>> bf.size()
        1
    """

    def __init__(self, capacity: int = 100000, error_rate: float = 0.001) -> None:
        """初始化内存版布隆过滤器。

        Args:
            capacity: 预期最大 URL 数量。
            error_rate: 目标误判率。
        """
        self._lock = threading.Lock()
        self._bf = ScalableBloomFilter(
            initial_capacity=capacity,
            error_rate=error_rate,
        )
        self._capacity = capacity
        self._error_rate = error_rate
        logger.info(
            "MemoryBloomFilter 初始化完成 capacity=%d error_rate=%.4f",
            capacity,
            error_rate,
        )

    def add(self, url: str) -> bool:
        """线程安全地添加 URL。

        Args:
            url: 待添加的 URL 字符串。

        Returns:
            True 表示新 URL，False 表示可能已存在。
        """
        with self._lock:
            if url in self._bf:
                logger.debug("URL 重复（布隆过滤器命中）: %s", url)
                return False
            self._bf.add(url)
            logger.debug("URL 新增: %s (count=%d)", url, self._bf.count)
            return True

    def contains(self, url: str) -> bool:
        """线程安全地检查 URL 是否存在。"""
        with self._lock:
            return url in self._bf

    def size(self) -> int:
        """返回已添加的不同 URL 数量的近似值。"""
        return self._bf.count

    def clear(self) -> None:
        """清空布隆过滤器（线程安全）。"""
        with self._lock:
            self._bf = ScalableBloomFilter(
                initial_capacity=self._capacity,
                error_rate=self._error_rate,
            )
            logger.info("MemoryBloomFilter 已清空")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _compute_bloom_params(capacity: int, error_rate: float) -> Dict[str, int]:
    """根据预期容量和误判率计算布隆过滤器参数。

    m = -n·ln(p) / (ln 2)²   （比特数组大小）
    k = (m/n) · ln 2          （哈希函数个数）

    Args:
        capacity: 预期最大元素数量 n。
        error_rate: 目标误判率 p。

    Returns:
        包含 m 和 k 的字典。
    """
    n = float(capacity)
    p = float(error_rate)
    m = int(math.ceil(-(n * math.log(p)) / (math.log(2) ** 2)))
    k = int(round((m / n) * math.log(2)))
    return {"m": max(m, 1), "k": max(k, 1)}


def _compute_hashes(url: str, m: int, k: int) -> list:
    """使用双重哈希技术生成 k 个比特位偏移量。

    采用 Kirsch-Mitzenmacher 方法：
    h_i(x) = (h1(x) + i * h2(x)) % m

    Args:
        url: 待哈希的 URL 字符串。
        m: 比特数组大小。
        k: 需要的哈希函数数量。

    Returns:
        k 个 [0, m) 范围内的整数偏移量列表。
    """
    raw = url.encode("utf-8")
    h1 = int(hashlib.sha256(raw).hexdigest(), 16)
    h2 = int(hashlib.md5(raw).hexdigest(), 16)
    return [(h1 + i * h2) % m for i in range(k)]


# Redis Lua 脚本：原子化 add 操作
# KEYS[1]: 布隆过滤器 bitmap key
# KEYS[2]: 布隆过滤器 meta key (hash)
# ARGV[1..k]: k 个比特位偏移量
_LUA_ADD_SCRIPT = """
local bitmap = KEYS[1]
local meta   = KEYS[2]
local bits   = ARGV

-- 检查所有比特位是否均已置 1
for i = 1, #bits do
    if redis.call('GETBIT', bitmap, tonumber(bits[i])) == 0 then
        -- 存在未置 1 的位，这是新 URL
        for j = 1, #bits do
            redis.call('SETBIT', bitmap, tonumber(bits[j]), 1)
        end
        redis.call('HINCRBY', meta, 'count', 1)
        return 1
    end
end
return 0
"""

# Redis Lua 脚本：原子化 clear 操作
_LUA_CLEAR_SCRIPT = """
redis.call('DEL', KEYS[1])
redis.call('DEL', KEYS[2])
return 1
"""


# ---------------------------------------------------------------------------
# Redis 版实现
# ---------------------------------------------------------------------------


class RedisBloomFilter(URLBloomFilterBackend):
    """基于 Redis Bitmap 的分布式布隆过滤器。

    使用 Redis SETBIT/GETBIT + Lua 脚本实现原子化 add 操作，支持多 Worker
    （多进程）共享同一 Redis 后端。哈希函数采用双重哈希（Kirsch-Mitzenmacher），
    sha256 + md5 组合生成 k 个比特位。

    连接失败时抛出 redis.exceptions.ConnectionError，不静默降级。

    Examples:
        >>> bf = RedisBloomFilter(capacity=100000, error_rate=0.001)
        >>> bf.add("https://example.com/page1")
        True
        >>> bf.contains("https://example.com/page1")
        True
        >>> bf.size()
        1
    """

    _KEY_PREFIX = "crawl4ai:bloom"

    def __init__(
        self,
        capacity: int = 100000,
        error_rate: float = 0.001,
        redis_url: Optional[str] = None,
        key_prefix: str = "",
    ) -> None:
        """初始化 Redis 版布隆过滤器。

        Args:
            capacity: 预期最大 URL 数量，用于计算比特数组大小。
            error_rate: 目标误判率。
            redis_url: Redis 连接地址，默认从 REDIS_URL 环境变量读取，
                回退为 redis://localhost:6379/0。
            key_prefix: 自定义 Redis Key 前缀，用于多个爬虫实例隔离。

        Raises:
            redis.exceptions.ConnectionError: Redis 连接失败时抛出。
        """
        params = _compute_bloom_params(capacity, error_rate)
        self._m = params["m"]
        self._k = params["k"]
        self._capacity = capacity
        self._error_rate = error_rate

        url = redis_url or DEFAULT_REDIS_URL
        self._redis = redis.Redis.from_url(
            url,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        # 连接验证
        self._redis.ping()

        prefix = key_prefix or self._KEY_PREFIX
        self._bitmap_key = f"{prefix}:bitmap"
        self._meta_key = f"{prefix}:meta"

        # 注册 Lua 脚本
        self._lua_add = self._redis.register_script(_LUA_ADD_SCRIPT)
        self._lua_clear = self._redis.register_script(_LUA_CLEAR_SCRIPT)

        # 初始化元数据
        if not self._redis.exists(self._meta_key):
            self._redis.hset(self._meta_key, mapping={"count": 0, "m": self._m, "k": self._k})

        logger.info(
            "RedisBloomFilter 初始化完成 capacity=%d error_rate=%.4f "
            "m=%d k=%d redis_url=%s",
            capacity,
            error_rate,
            self._m,
            self._k,
            url,
        )

    def add(self, url: str) -> bool:
        """原子化添加 URL（Lua 脚本保证原子性）。

        Args:
            url: 待添加的 URL 字符串。

        Returns:
            True 表示新 URL，False 表示可能已存在。
        """
        offsets = _compute_hashes(url, self._m, self._k)
        result = self._lua_add(
            keys=[self._bitmap_key, self._meta_key],
            args=[str(o) for o in offsets],
        )
        is_new = bool(int(result))
        if is_new:
            logger.debug("URL 新增 (Redis): %s", url)
        else:
            logger.debug("URL 重复 (Redis 命中): %s", url)
        return is_new

    def contains(self, url: str) -> bool:
        """检查 URL 是否可能已存在。

        读取操作无需 Lua 脚本，GETBIT 本身是原子的。
        """
        offsets = _compute_hashes(url, self._m, self._k)
        pipe = self._redis.pipeline()
        for offset in offsets:
            pipe.getbit(self._bitmap_key, offset)
        bits = pipe.execute()
        return all(b == 1 for b in bits)

    def size(self) -> int:
        """返回当前计数（从 Redis meta 读取）。"""
        raw = self._redis.hget(self._meta_key, "count")
        return int(raw) if raw else 0

    def clear(self) -> None:
        """清空布隆过滤器（Lua 脚本原子删除）。"""
        self._lua_clear(keys=[self._bitmap_key, self._meta_key])
        # 重新初始化元数据
        self._redis.hset(self._meta_key, mapping={"count": 0, "m": self._m, "k": self._k})
        logger.info("RedisBloomFilter 已清空")

    def close(self) -> None:
        """关闭 Redis 连接。"""
        self._redis.close()
        logger.info("RedisBloomFilter 连接已关闭")


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------


def create_bloom_filter(
    backend: str = "memory",
    capacity: int = 100000,
    error_rate: float = 0.001,
    redis_url: Optional[str] = None,
    **kwargs: Any,
) -> URLBloomFilterBackend:
    """布隆过滤器工厂函数，根据 backend 参数创建对应实例。

    Args:
        backend: 后端标识，"memory" 或 "redis"。
        capacity: 预期最大 URL 数量。
        error_rate: 目标误判率。
        redis_url: Redis 连接地址（仅 backend="redis" 时有效），
            默认从 REDIS_URL 环境变量读取。
        **kwargs: 传递给具体后端的额外参数（如 key_prefix）。

    Returns:
        URLBloomFilterBackend 实例。

    Raises:
        ValueError: backend 不在支持的列表中。
        redis.exceptions.ConnectionError: Redis 连接失败（backend="redis" 时）。

    Examples:
        >>> bf = create_bloom_filter("memory", capacity=1000)
        >>> bf = create_bloom_filter("redis", redis_url="redis://localhost:6379/0")
    """
    backend_lower = backend.lower()
    if backend_lower == "memory":
        return MemoryBloomFilter(capacity=capacity, error_rate=error_rate, **kwargs)
    elif backend_lower == "redis":
        return RedisBloomFilter(
            capacity=capacity,
            error_rate=error_rate,
            redis_url=redis_url,
            **kwargs,
        )
    else:
        raise ValueError(
            f"不支持的 backend: {backend!r}，可选值: 'memory', 'redis'"
        )
