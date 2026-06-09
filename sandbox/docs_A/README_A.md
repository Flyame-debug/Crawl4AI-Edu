# 成员 A — 爬虫与异步任务模块使用说明

## 环境准备

```bash
conda create -n crawlai-edu python=3.11 -y
conda activate crawlai-edu
pip install -r sandbox/requirements.txt
playwright install chromium    # 仅 use_render=True 时需要
```

所有命令在项目根目录 `E:\SX2606\Crawl4AI-Edu` 下执行。

---

## 快速开始

### 命令行运行爬虫

```bash
python sandbox/run_crawler.py <种子URL> [最大深度] [配置文件路径]
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `seed_url` | 是 | — | 种子 URL，爬虫起始页 |
| `max_depth` | 否 | 2 | BFS 最大深度，种子页深度为 0，须 ≥ 1 |
| `config_path` | 否 | `sandbox/crawler_config.json` | JSON 配置文件路径 |

示例：

```bash
# 使用默认配置，深度 2
python sandbox/run_crawler.py https://example.com

# 指定深度 1
python sandbox/run_crawler.py https://example.com 1

# 使用自定义配置文件
python sandbox/run_crawler.py https://example.com 2 my_config.json
```

输出 HTML 文件保存在 `sandbox/data/html/`，下载的图片保存在 `sandbox/data/images/`。

---

## 配置文件

默认配置文件为 `sandbox/crawler_config.json`，结构如下：

```json
{
  "default_allowed_domains": [],
  "white_list_patterns": [".*"],
  "concurrency": 5,
  "request_delay": 1.0,
  "max_depth": 2
}
```

字段说明：

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `default_allowed_domains` | `list[str]` | `[]`（允许所有域名） | 域名白名单，如 `["example.com", "iana.org"]` |
| `white_list_patterns` | `list[str]` | `[".*"]`（允许所有路径） | URL 路径正则白名单，如 `["/docs/.*", "/blog/.*"]` |
| `concurrency` | `int` | 5 | 同时处理的最大页面数 |
| `request_delay` | `float` | 1.0 | 每次请求前的等待秒数（礼貌爬取） |
| `max_depth` | `int` | 2 | BFS 最大深度（命令行参数可覆盖） |

优先级：命令行参数 > 配置文件 > 内置默认值。

---

## 各模块导入与调用

### A5 — 独立爬虫（推荐入口）

```python
from standalone_crawler import crawl

stats = await crawl(
    seed_url="https://example.com",
    max_depth=2,
    max_concurrent=5,
    enable_dead_check=False,
    allowed_domains=[],                    # [] = 允许所有域名
    white_list_patterns=[],                # [] = 允许所有路径
    request_delay=1.0,
    config_path="sandbox/crawler_config.json",  # None = 跳过配置文件
)
print(stats.report())
```

### A1 — 异步抓取引擎

```python
from fetcher import async_fetch, FetchError

# 静态抓取（aiohttp）
html = await async_fetch("https://example.com")

# 动态渲染（Playwright — 需先 playwright install chromium）
html = await async_fetch("https://spa.example.com", use_render=True)

# 带重试和延迟
html = await async_fetch("https://example.com", delay=2.0, max_retries=3)
```

### A2 — 链接提取与 URL 去重

```python
from link import extract_links, create_bloom_filter

# 提取链接（空列表表示不限制域名 / 路径）
links = extract_links(
    html,
    base_url="https://example.com",
    allowed_domains=[],            # [] = 允许所有域名
    white_list_patterns=[],        # [] = 允许所有路径
)

# 域名白名单模式
links = extract_links(
    html,
    base_url="https://example.com",
    allowed_domains=[".iana.org", ".example.com"],
    white_list_patterns=["/docs/.*", "/blog/.*"],
)

# 布隆过滤器（内存版 — 单进程）
bf = create_bloom_filter("memory", capacity=100000, error_rate=0.001)
bf.add("https://example.com/page1")       # → True（新 URL）
bf.add("https://example.com/page1")       # → False（重复）
bf.contains("https://example.com/page1")  # → True
bf.size()                                  # → 1

# 布隆过滤器（Redis 版 — 多 Worker 共享，需 Redis 运行中）
bf = create_bloom_filter("redis", redis_url="redis://localhost:6379/0")
```

### A3 — 图片下载

```python
from image_downloader import download_images

mapping = await download_images(
    html,
    base_url="https://example.com",
    output_dir="sandbox/data/images",
    concurrency=5,
)
# 返回 {原始URL: 本地绝对路径} 字典
for src_url, local_path in mapping.items():
    print(f"{src_url} → {local_path}")
```

### A4 — 死链检测

```python
from dead_link_checker import check_dead_links

dead = await check_dead_links(
    ["https://example.com/ok", "https://example.com/404"],
    max_concurrent=10,
    retries=3,
)
print(f"死链: {dead}")
```

---

## 模块架构与依赖关系

```
sandbox/
├── fetcher/                 # A1 — 异步 HTTP / Playwright 抓取引擎
│   ├── core.py              #   async_fetch() 主函数
│   ├── exceptions.py        #   FetchError 异常类
│   └── ua_pool.py           #   User-Agent 随机池
│
├── link/                    # A2 — 链接发现与 URL 去重
│   ├── extractor.py         #   extract_links() — 基于 Scrapy LxmlLinkExtractor
│   ├── bloom_filter.py      #   create_bloom_filter() — Memory / Redis 后端
│   └── utils.py             #   URL 有效性检查、域名规范化
│
├── image_downloader/        # A3 — 图片提取与并发下载
│   ├── core.py              #   download_images() 主函数
│   └── utils.py             #   Content-Type / Content-Disposition 解析
│
├── dead_link_checker/       # A4 — 死链并发检测（HEAD 请求）
│   └── checker.py           #   check_dead_links() 主函数
│
├── standalone_crawler/      # A5 — 独立爬虫组装模块
│   ├── __init__.py          #   导出 crawl
│   ├── crawler.py           #   BFS 爬虫核心 + load_config()
│   ├── handlers.py          #   单页处理（抓取→存 HTML→下图片→提链接）
│   ├── stats.py             #   统计收集与报告
│   ├── utils.py             #   辅助函数（URL 哈希、规范化、日志）
│   └── test_crawler.py      #   集成自测脚本
│
├── crawler_config.json      # 爬虫配置文件
├── run_crawler.py           # 命令行入口
└── requirements.txt         # A 模块依赖清单
```

依赖关系：A5 → A1 / A2 / A3，A5 可选依赖 A4。各 A1–A4 模块相互独立。

---

## 运行自测

```bash
# 单元级导入验证
python -c "import sandbox.standalone_crawler.utils"
python -c "import sandbox.standalone_crawler.handlers"
python -c "import sandbox.standalone_crawler.stats"
python -c "import sandbox.standalone_crawler.crawler"

# 集成测试（使用 httpbin.org，失败时自动回退到 example.com）
python -m sandbox.standalone_crawler.test_crawler
```

## 注意事项

爬虫使用广度优先策略，同一 URL 通过布隆过滤器去重，仅抓取一次。任何页面抓取异常不会导致整体崩溃，会记录日志并继续处理其他 URL。`playwright` 仅在使用 `use_render=True` 时才需要，默认的静态抓取不依赖它。Redis 依赖仅在使用布隆过滤器的 `backend="redis"` 时需要，默认的 `"memory"` 后端无需 Redis。所有模块均可独立使用，不依赖 Django、Celery 或数据库。
