# A 模块工作总览

## 项目背景与角色定位

成员 A 负责 Crawl4AI 系统的**爬虫与异步任务**模块，实现从网页抓取、链接发现、内容转换、AI 规则生成到反爬检测和质量报告的全链路能力。技术栈：Python 3.11 + aiohttp + Playwright + Crawl4AI + Scrapy + BeautifulSoup。

---

## 模块清单

| 子包/模块 | 路径 | 职责 |
|---|---|---|
| `standalone_crawler` | `sandbox/standalone_crawler/` | 爬虫核心：BFS 调度、页面处理、Stats、API 客户端、Crawl4AI 集成 |
| `fetcher` | `sandbox/fetcher/` | HTTP 抓取引擎（aiohttp 静态 + Playwright 动态渲染） |
| `link` | `sandbox/link/` | 链接提取（Scrapy）与去重（Bloom Filter，内存/Redis 双后端） |
| `image_downloader` | `sandbox/image_downloader/` | 图片提取与并发下载（aiohttp，自动重试） |
| `dead_link_checker` | `sandbox/dead_link_checker/` | 死链检测（HEAD 请求 + 指数退避重试） |
| `ai_client` | `sandbox/ai_client/` | Ollama 本地 LLM 客户端 + Prompt 模板 |
| `script_generator` | `sandbox/script_generator/` | AI 驱动 XPath/CSS 规则生成 + 兜底逻辑 |
| `crawler` | `sandbox/crawler/` | 反爬检测 + 质量报告生成 |
| `seed_generators` | `sandbox/seed_generators/` | 种子 URL 生成器（华科教师 AJAX API 分页采集） |
| `scripts` | `sandbox/scripts/` | 运维脚本（metadata 构建、主页重渲染） |
| `config` | `sandbox/config/` | 站点级抓取配置（如 `hust_faculty.json`） |
| `seeds` | `sandbox/seeds/` | 预生成的种子 URL 文件 |

---

## 核心功能说明

### 爬虫核心（standalone_crawler）

BFS 广度优先爬虫，深度可控，并发受 `asyncio.Semaphore` 约束。入口为 `crawl()` 函数，支持三种模式：**Local 模式**从本地种子文件和 JSON 配置启动一次性爬取；**API Worker 模式**轮询后端待爬种子，上报结果；**Preview 模式**限制页数，仅本地输出。核心引擎 `_run_bfs_crawl` 按层并发处理页面，每层完成后收集新链接进入下一层。支持断点续爬（`--resume`），每次成功抓取后写入增量文件。

### 页面处理（handlers.process_page）

单页处理流水线：获取 HTML → Crawl4AI 转 Markdown（失败降级 readability+markdownify）→ 图片上传/本地保存 → 链接提取与去重。API 模式下图片以 base64 上传，页面快照通过 `save_page_snapshot` 提交后端。Local 模式将 HTML/MD/图片写入磁盘并记录 mapping。

### 链接发现与去重（link）

`extract_links` 基于 Scrapy `LxmlLinkExtractor`，支持域名白名单和路径正则白名单，自动过滤 `javascript:`、`mailto:` 等伪协议。去重使用可插拔 Bloom Filter：`MemoryBloomFilter`（pybloom_live，线程安全）和 `RedisBloomFilter`（Redis Bitmap，多 Worker 共享）。工厂函数 `create_bloom_filter("memory"|"redis")` 统一创建。

### Crawl4AI 集成（crawl4ai_client + markdown_converter）

`convert_with_crawl4ai(html)` 将 HTML 通过 Crawl4AI 的 `raw:` URL 方案转为 Markdown。30 秒超时内完成则返回；超时、ImportError 或运行时异常自动降级到 `html_to_markdown_simple`（readability-lxml 提取正文 + markdownify 转换）。降级路径确保在 Crawl4AI 不可用时系统仍能产出可读文本。

### AI 脚本生成（ai_client + script_generator）

三阶段流水线：**简化** HTML 为 `tag[class='name']` 格式的树摘要（≤3000 字符）→ **推理** 加载 Prompt 模板并调用 Ollama `qwen2:7b` 生成 JSON → **兜底** JSON 解析失败或 AI 不可用时，用中文关键词（姓名、邮箱、职称等）生成 fallback 规则。Ollama 连接失败或超时自动降级，系统始终可用。

### 加密监测与质量报告（crawler）

`analyze_anti_crawl` 从状态码（403/429/503）、内容指纹（Cloudflare、CAPTCHA、Access Denied 等 15 种模式）、JS 混淆（`eval+unescape`、`_cf_chl`、`atob` 等 11 种模式）三个维度检测反爬，已集成到 `process_page` 的抓取成功和失败两条路径。

`generate_quality_report` 在每次爬取结束时自动生成 JSON 报告：成功率、平均正文长度、图片缺失率、失败 URL 按类别（Timeout/Anti-Crawl/4xx/5xx/DNS/Connection/SSL/Parse）归因统计。

---

## 对外暴露的主要函数/类

### 爬虫调度

```python
from standalone_crawler import crawl

async def crawl(
    seed_url: str | None = None,
    max_depth: int | None = None,
    max_concurrent: int | None = None,
    enable_dead_check: bool = False,
    allowed_domains: list[str] | None = None,
    white_list_patterns: list[str] | None = None,
    request_delay: float | None = None,
    config_path: str | None = "sandbox/crawler_config.json",
    api_client: APIClient | None = None,
    seed_urls: list[str] | None = None,
    output_dir: str | None = None,
    task_type: str = "full",        # "preview" | "full"
    preview_limit: int = 10,
) -> Statistics | None:
```

**说明**：爬虫主入口，支持 Local / API Worker / Preview 三种模式。Local 模式返回 `Statistics` 对象；API Worker 模式无限循环不返回。命令行入口：`python sandbox/run_crawler.py <seed_url> [max_depth]`。

### 单页处理

```python
from standalone_crawler.handlers import process_page

async def process_page(
    url: str,
    current_depth: int,
    bloom_filter: Any,
    allowed_domains: list[str] | None = None,
    white_list_patterns: list[str] | None = None,
    api_client: APIClient | None = None,
    task_id: str | None = None,
    seed_meta: dict[str, Any] | None = None,
    image_concurrency: int = 5,
    output_dir: str | None = None,
    mapping_path: str | None = None,
) -> dict[str, Any]:
```

**返回值**：`{"success": bool, "url": str, "depth": int, "links": [...], "images": [...], "html": str|None, "markdown": str|None, "error": str|None, "anti_crawl": dict|None}`。

### AI 规则生成

```python
from script_generator.generate_rules import generate_extraction_rules

def generate_extraction_rules(html: str, instruction: str) -> dict[str, Any]:
```

**返回值**：`{"xpath": str, "css": str, "confidence": float, "source": "ai"|"fallback"}`。`source: "fallback"` 表示 Ollama 不可用，已走关键词兜底。

### HTML → Markdown 转换

```python
from standalone_crawler.crawl4ai_client import convert_with_crawl4ai

async def convert_with_crawl4ai(html: str, timeout: float = 30.0) -> str:
```

**说明**：优先使用 Crawl4AI，失败时自动降级到 readability+markdownify。永不抛出异常。

### 反爬检测

```python
from crawler.anti_detect import analyze_anti_crawl

def analyze_anti_crawl(url: str, html: str | None, status_code: int) -> dict[str, Any]:
```

**返回值**：`{"has_encryption": bool, "suggest_render": bool, "message": str}`。

### 质量报告

```python
from crawler.quality_report import generate_quality_report

def generate_quality_report(
    task_stats: Any,               # Statistics-like object
    page_results: list[dict[str, Any]],
    output_dir: str,
    *, task_label: str | None = None,
) -> str:                          # 返回报告文件绝对路径
```

### HTML 抓取

```python
from fetcher import async_fetch, FetchError

async def async_fetch(
    url: str,
    use_render: bool = False,
    delay: float = 1.0,
    domain_semaphore: asyncio.Semaphore | None = None,
    max_retries: int = 2,
) -> str:                          # 返回 HTML 文本，失败抛出 FetchError
```

### 链接提取

```python
from link import extract_links

def extract_links(
    html: str,
    base_url: str,
    allowed_domains: list[str],
    white_list_patterns: list[str],
) -> list[str]:
```

### 图片下载

```python
from image_downloader import download_images

async def download_images(
    html: str,
    base_url: str,
    output_dir: str = "sandbox/images",
    concurrency: int = 5,
) -> dict[str, str]:               # {原始URL: 本地路径}
```

### 布隆过滤器

```python
from link import create_bloom_filter

def create_bloom_filter(backend: str = "memory") -> URLBloomFilterBackend:
```

### 死链检测

```python
from dead_link_checker import check_dead_links

async def check_dead_links(
    urls: list[str],
    max_concurrent: int = 10,
    retries: int = 3,
) -> list[str]:                    # 返回死链列表
```

### API 客户端（供后端调用方使用）

```python
from standalone_crawler import APIClient

class APIClient:
    def __init__(self, base_url: str | None = None, max_retries: int = 3, timeout: int = 30): ...
    async def get_config(self) -> dict: ...
    async def get_pending_seeds(self, limit: int = 10) -> dict: ...
    async def update_seed_status(self, url: str, status: str) -> dict: ...
    async def start_crawl_task(self, seed_url: str, max_depth: int | None = None, config: dict | None = None) -> dict: ...
    async def upload_image_base64(self, image_base64_str: str, filename: str) -> dict: ...
    async def save_page_snapshot(self, url: str, markdown: str, category: str | None = None, images: list | None = None, html: str | None = None) -> dict: ...
    async def report_task_result(self, task_id: str, status: str, total_pages: int | None = None, success_pages: int | None = None, failed_pages: int | None = None, report: str | None = None, error_message: str | None = None) -> dict: ...
```

### 种子生成

```python
from seed_generators.generate_faculty_seeds import generate_seeds

def generate_seeds() -> int:       # 返回生成的种子数量，写入 seeds/faculty_seeds.txt
```

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CRAWLER_BACKEND_URL` | `http://127.0.0.1:8000` | 后端 API 地址 |
| `USE_API` | `false` | 是否启用 API 模式 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址（Bloom Filter Redis 后端） |
| `ENABLE_GRACEFUL_EXIT` | `1` | 是否启用优雅退出（SIGINT/SIGTERM） |

### 配置文件

- **爬虫全局配置**：`sandbox/crawler_config.json`（concurrency、request_delay、max_depth、allowed_domains、white_list_patterns）
- **站点级配置**：`sandbox/config/schools/*.json`（如 `hust_faculty.json`，可通过 `load_school_config(domain)` 按域名加载）
- **Ollama 配置**：硬编码在 `ollama_client.py`（`_OLLAMA_BASE_URL="http://localhost:11434"`、`_DEFAULT_MODEL="qwen2:7b"`、`_REQUEST_TIMEOUT=30`）

### 依赖项

见 `sandbox/requirements.txt`：`aiohttp`、`playwright`、`scrapy`、`pybloom-live`、`redis`、`beautifulsoup4`、`crawl4ai`、`readability-lxml`、`markdownify`、`pytest`、`pytest-asyncio`。安装方式：`conda activate crawlai-edu && pip install -r sandbox/requirements.txt`。

---

## 测试与运行方式

### 运行爬虫

```bash
conda activate crawlai-edu

# Local 模式：单种子
python sandbox/run_crawler.py https://example.com

# Local 模式：种子列表文件
python sandbox/run_crawler.py --seed-list sandbox/seeds/faculty_seeds_sample.txt

# Preview 模式（限制 5 页，仅本地输出，不调 API）
python sandbox/run_crawler.py https://example.com --task-type preview --preview-limit 5

# API Worker 模式（轮询后端待爬种子）
python sandbox/run_crawler.py --worker --backend-url http://192.168.1.1:8000

# API 单次模式
python sandbox/run_crawler.py --use-api --seed https://example.com
```

### 测试各模块

```bash
conda activate crawlai-edu
cd sandbox

# 爬虫核心
python -m standalone_crawler.crawler        # BFS + 报告生成
python -m standalone_crawler.handlers       # 单页处理 + 反爬检测
python -m standalone_crawler.crawl4ai_client # Crawl4AI 转换
python -m standalone_crawler.stats          # 统计对象
python -m standalone_crawler.markdown_converter # 降级转换
python -m standalone_crawler.api_client     # API 客户端结构
python -m standalone_crawler.config_loader  # 站点配置加载
python -m standalone_crawler.utils          # 工具函数

# AI 脚本生成
python -m ai_client.ollama_client           # Ollama 连接测试
python -m script_generator.generate_rules   # 规则生成（需 Ollama 运行）

# 反爬 + 质量报告
python -m crawler.anti_detect               # 反爬检测
python -m crawler.quality_report            # 报告生成

# 抓取引擎
python -m fetcher.test_fetch                # 抓取集成测试

# 链接 + 去重
python link/tests.py                        # 链接提取和 Bloom Filter 全量测试

# 图片下载
python -m image_downloader.core             # 图片下载测试

# 种子生成
python seed_generators/generate_faculty_seeds.py
```
