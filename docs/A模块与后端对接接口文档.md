# A 模块与后端对接接口文档

本文档面向成员 C（后端），分为三部分：A 模块可供后端调用的函数接口、A 模块依赖的 REST API 前置条件、以及基于代码审查的优化建议。

---

## 第一部分：A 模块提供给后端的服务/接口

以下函数可由后端（成员 C）通过 Python 导入直接调用，无需经过 HTTP。

### 1. generate_extraction_rules — AI 规则生成

- **用途**：根据用户自然语言指令和目标页面 HTML，生成 XPath/CSS 采集规则。
- **输入**：

| 参数 | 类型 | 说明 |
|---|---|---|
| `html` | `str` | 目标页面的原始 HTML 字符串 |
| `instruction` | `str` | 自然语言指令，如 `"提取所有教师姓名和邮箱"` |

- **输出**：

```python
{
    "xpath": "//span[@class='name']/text()",
    "css": "div.teacher span.name",
    "confidence": 0.95,
    "source": "ai"       # "ai" 或 "fallback"（Ollama 不可用时的兜底）
}
```

- **所在文件**：`sandbox/script_generator/generate_rules.py`
- **导入路径**：`from script_generator.generate_rules import generate_extraction_rules`
- **前置条件**：Ollama 服务运行在 `localhost:11434`，模型 `qwen2:7b` 已加载。离线时自动降级为关键词兜底规则（`source: "fallback"`）。
- **调用示例**：

```python
from script_generator.generate_rules import generate_extraction_rules

rules = generate_extraction_rules(
    html='<div class="teacher"><span class="name">张三</span></div>',
    instruction="提取所有教师姓名",
)
print(rules["xpath"])  # //span[@class='name']/text()
```

---

### 2. convert_with_crawl4ai — HTML 转 Markdown

- **用途**：将 HTML 转为 Markdown，优先 Crawl4AI，失败时降级 readability+markdownify。
- **输入**：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `html` | `str` | — | 原始 HTML |
| `timeout` | `float` | `30.0` | Crawl4AI 超时秒数 |

- **输出**：`str` — Markdown 文本。永不抛出异常。
- **所在文件**：`sandbox/standalone_crawler/crawl4ai_client.py`
- **导入路径**：`from standalone_crawler.crawl4ai_client import convert_with_crawl4ai`
- **调用示例**：

```python
from standalone_crawler.crawl4ai_client import convert_with_crawl4ai

markdown = await convert_with_crawl4ai("<html>...page content...</html>")
```

---

### 3. analyze_anti_crawl — 反爬检测

- **用途**：检测页面是否存在 WAF/CAPTCHA/JS 挑战等反爬信号。
- **输入**：

| 参数 | 类型 | 说明 |
|---|---|---|
| `url` | `str` | 目标页面 URL |
| `html` | `str \| None` | 页面 HTML（抓取失败时为 `None`） |
| `status_code` | `int` | HTTP 状态码（连接失败传 `0`） |

- **输出**：

```python
{
    "has_encryption": False,     # 是否检测到反爬信号
    "suggest_render": False,     # 是否建议改用 Playwright 渲染
    "message": "No anti-crawl signals detected."
}
```

- **所在文件**：`sandbox/crawler/anti_detect.py`
- **导入路径**：`from crawler.anti_detect import analyze_anti_crawl`
- **调用示例**：

```python
from crawler.anti_detect import analyze_anti_crawl

result = analyze_anti_crawl("https://example.com", html, 200)
if result["has_encryption"]:
    # 记录告警或切换渲染模式
    pass
```

---

### 4. generate_quality_report — 质量报告

- **用途**：基于爬取统计数据生成结构化 JSON 报告。
- **输入**：

| 参数 | 类型 | 说明 |
|---|---|---|
| `task_stats` | `Statistics` | 包含 `total`/`success`/`failed`/`total_images`/`start_time`/`end_time` 的对象 |
| `page_results` | `list[dict]` | `process_page` 返回的逐页结果列表 |
| `output_dir` | `str` | 报告输出目录（自动创建） |
| `task_label` | `str \| None` | 可选任务标签 |

- **输出**：`str` — 生成的 JSON 报告文件绝对路径。
- **所在文件**：`sandbox/crawler/quality_report.py`
- **导入路径**：`from crawler.quality_report import generate_quality_report`
- **调用示例**：

```python
from crawler.quality_report import generate_quality_report

path = generate_quality_report(stats, page_results, "sandbox/data/reports", task_label="batch-01")
print(f"报告已生成: {path}")
```

---

### 5. APIClient — 后端通信客户端

- **用途**：封装对后端 7 个 REST 端点的异步调用，含指数退避重试。
- **所在文件**：`sandbox/standalone_crawler/api_client.py`
- **导入路径**：`from standalone_crawler import APIClient`
- **公开方法**：

| 方法 | 对应端点 | 说明 |
|---|---|---|
| `get_config()` | `GET /api/crawler/config/db/` | 获取爬虫配置 |
| `get_pending_seeds(limit)` | `GET /api/seeds/pending/` | 获取待爬种子 |
| `update_seed_status(url, status)` | `POST /api/seeds/status/` | 更新种子状态 |
| `start_crawl_task(seed_url, max_depth, config)` | `POST /api/crawl/start/` | 启动任务，返回 task_id |
| `upload_image_base64(b64, filename)` | `POST /api/images/upload/` | 上传图片（base64） |
| `save_page_snapshot(url, markdown, ...)` | `POST /api/pagesnapshot/` | 保存页面快照 |
| `report_task_result(task_id, status, ...)` | `POST /api/tasks/{id}/result/` | 上报任务结果 |

---

### 6. crawl — 爬虫调度入口

- **用途**：完整的 BFS 爬取流程，支持 Local / API Worker / Preview 三种模式。
- **所在文件**：`sandbox/standalone_crawler/crawler.py`
- **导入路径**：`from standalone_crawler import crawl`
- **调用方式**：异步函数，可直接在 Python 中调用，也可通过命令行入口 `python sandbox/run_crawler.py`。
- **命令行调用示例**：

```bash
# 本地模式
python sandbox/run_crawler.py https://example.com 2

# 预览模式
python sandbox/run_crawler.py https://example.com --task-type preview --preview-limit 10

# API Worker 模式
python sandbox/run_crawler.py --worker --backend-url http://192.168.1.1:8000
```

- **Python 调用示例**：

```python
from standalone_crawler import crawl

stats = await crawl(
    seed_url="https://example.com",
    max_depth=2,
    max_concurrent=5,
    task_type="full",
)
print(stats.report())
```

---

### 7. 工具函数一览

| 函数 | 文件 | 用途 |
|---|---|---|
| `async_fetch(url, use_render, delay, ...)` | `fetcher/core.py` | 异步 HTTP 抓取（aiohttp / Playwright） |
| `extract_links(html, base_url, domains, patterns)` | `link/extractor.py` | 基于 Scrapy 的链接提取 |
| `create_bloom_filter(backend)` | `link/bloom_filter.py` | 布隆过滤器工厂（memory/redis） |
| `download_images(html, base_url, output_dir, concurrency)` | `image_downloader/core.py` | 图片提取与并发下载 |
| `check_dead_links(urls, max_concurrent, retries)` | `dead_link_checker/checker.py` | 异步死链检测 |
| `ask_ollama(prompt, model)` | `ai_client/ollama_client.py` | Ollama 同步调用 |
| `load_config(config_path)` | `standalone_crawler/crawler.py` | JSON 配置文件加载 |
| `load_school_config(domain)` | `standalone_crawler/config_loader.py` | 按域名加载站点配置 |
| `html_to_markdown_simple(html)` | `standalone_crawler/markdown_converter.py` | 纯 Python Markdown 转换（降级方案） |
| `normalize_url(url, base_url)` | `standalone_crawler/utils.py` | URL 规范化和片段移除 |
| `generate_seeds()` | `seed_generators/generate_faculty_seeds.py` | HUST 教师种子 URL 生成 |

---

## 第二部分：后端需提供给 A 模块的接口（前置依赖）

以下 REST API 是 A 模块在 API Worker 模式下正常运行的**必需依赖**。缺失任一接口将导致对应功能降级或失败。

### 接口 1：GET /api/crawler/config/db/

- **用途**：获取爬虫全局配置（并发数、深度、白名单等）。
- **调用位置**：`standalone_crawler/api_client.py:68` → `APIClient.get_config()`
- **请求**：无参数。
- **响应**：

```json
{
  "concurrency": 5,
  "request_delay": 1.0,
  "max_depth": 2,
  "allowed_domains": [],
  "white_list_patterns": [],
  "enable_dead_check": false
}
```

- **必须性**：✅ 必须 — Worker 模式每 10 轮刷新一次配置，缺失则使用上次缓存或默认值。

### 接口 2：GET /api/seeds/pending/?limit=N

- **用途**：获取待爬取的种子 URL 列表。
- **调用位置**：`standalone_crawler/api_client.py:83` → `APIClient.get_pending_seeds()`
- **请求参数**：`limit`（int，可选，默认 10）。
- **响应**：

```json
{
  "count": 3,
  "seeds": [
    {"id": 1, "url": "...", "school": "清华大学", "category": "师资", "need_render": false}
  ]
}
```

- **必须性**：✅ 必须 — Worker 模式的核心驱动，无待爬种子时休眠 `poll_interval` 秒后重试。

### 接口 3：POST /api/seeds/status/

- **用途**：更新种子状态（pending → crawling → success/failed/blocked）。
- **调用位置**：`standalone_crawler/api_client.py:101` → `APIClient.update_seed_status()`
- **请求体**：`{"url": "string", "status": "crawling|success|failed|blocked"}`
- **响应**：`{"status": "ok", "url": "...", "new_status": "..."}`
- **必须性**：✅ 必须 — 种子生命周期管理，缺失则后端状态与实际不符。

### 接口 4：POST /api/images/upload/

- **用途**：上传图片（base64 编码），返回 MinIO 存储地址。
- **调用位置**：`standalone_crawler/api_client.py:155` → `APIClient.upload_image_base64()`
- **请求体**：`{"image_base64": "...", "filename": "photo.jpg"}`
- **响应**：

```json
{"success": true, "url": "http://127.0.0.1:9000/crawl4ai/images/abc.jpg", "image_id": "abc"}
```

- **必须性**：✅ 必须（API 模式）— 图片上传失败仅记录日志，不阻断爬取。

### 接口 5：POST /api/pagesnapshot/

- **用途**：保存爬取的页面快照（HTML/Markdown + 图片引用）。
- **调用位置**：`standalone_crawler/api_client.py:189` → `APIClient.save_page_snapshot()`
- **请求体**：

```json
{
  "url": "https://...",
  "markdown": "# Title\n\nContent...",
  "html": "<html>...</html>",
  "category": "师资",
  "images": [{"original_url": "...", "stored_url": "http://minio/..."}]
}
```

- **响应**：`{"action": "created", "data": {"id": 123, ...}}`
- **必须性**：✅ 必须（API 模式）— 缺失则页面数据无法持久化到后端数据库。

### 接口 6：POST /api/crawl/start/

- **用途**：启动爬取任务，获取 `task_id` 用于后续结果上报。
- **调用位置**：`standalone_crawler/api_client.py:130` → `APIClient.start_crawl_task()`
- **请求体**：`{"seed_url": "...", "max_depth": 2, "config": {...}}`
- **响应**：

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Crawl task started successfully.",
  "status_url": "/api/crawl/status/.../",
  "created_at": "2026-06-15T10:00:00Z"
}
```

- **必须性**：✅ 必须（API 模式）— `task_id` 是后续上报结果的前置标识符。

### 接口 7：POST /api/tasks/{task_id}/result/

- **用途**：上报爬取任务的最终结果。
- **调用位置**：`standalone_crawler/api_client.py:231` → `APIClient.report_task_result()`
- **请求体**：

```json
{
  "status": "completed",
  "total_pages": 50,
  "success_pages": 48,
  "failed_pages": 2,
  "report": "抓取完成，成功率96%",
  "error_message": null
}
```

- **必须性**：✅ 必须（API 模式）— 后端需要此接口获知任务最终状态。

---

## 第三部分：优化建议与可扩展接口预留

### 短期优化建议

**1. 配置外置** — `ollama_client.py` 中的 `_OLLAMA_BASE_URL` 和 `_DEFAULT_MODEL` 硬编码在模块常量中。建议改为环境变量（`OLLAMA_BASE_URL`、`OLLAMA_MODEL`），方便切换模型或 Ollama 部署位置。

**2. 批量图片上传** — 当前 `upload_image_base64` 是逐张上传（`asyncio.Semaphore` 控制并发）。若后端支持批量接口（如 `POST /api/images/upload/batch/`），可显著减少 HTTP 往返次数。

**3. 接口幂等性** — `save_page_snapshot` 通过 `url` 字段去重（created/updated/skipped），这是好的实践。建议后端确保 `update_seed_status` 和 `report_task_result` 也具备幂等性，因为 Worker 可能在网络抖动时重试。

**4. Ollama 预热** — 冷启动时首次 `ask_ollama` 调用可能因模型加载超时（当前 30s 超时返回空字符串触发兜底）。建议在爬虫启动时额外增加 `ollama_client` 的预热调用或增加超时到 60s。

**5. 错误消息标准化** — `fetcher/core.py` 中的 `FetchError` 消息格式为 `f"HTTP {resp.status} for {url}"`，`handlers.py` 用正则 `r"HTTP (\d+)"` 解析。建议在 `FetchError` 中增加 `status_code` 属性字段，避免依赖字符串解析。

### 可扩展接口预留

**1. 插件化反爬策略** — `anti_detect.py` 当前内置检测模式列表。若后端能提供"反爬策略配置"接口（如 `GET /api/anti-crawl/rules/`），可将检测模式动态化，后端运营人员无需修改代码即可更新反爬指纹库。

**2. 分布式去重增强** — `RedisBloomFilter` 已实现基于 Redis Bitmap 的多 Worker 共享去重。若后续需要跨任务去重或持久化，可增加 `POST /api/bloom/check/` 和 `POST /api/bloom/add/` 接口，由后端统一管理去重状态。

**3. 动态种子注入** — Worker 模式当前仅通过 `get_pending_seeds` 拉取种子。可扩展 Webhook 回调（后端主动推送新种子），减少轮询延迟。建议预留 `POST /api/seeds/notify/` 或 WebSocket 通道。

**4. 渲染模式按 URL 自动切换** — `config_loader.py` 的 `render_for_depth` 和 `use_render` 字段已支持按深度配置渲染策略。若后端能提供"URL→渲染策略"的映射（通过 `GET /api/config/render-rules/`），可根据页面类型自动决定是否启用 Playwright。

**5. 报告 Webhook** — `generate_quality_report` 当前仅生成本地 JSON 文件。可扩展 `POST /api/reports/` 接口将报告自动提交到后端，方便运维面板展示。建议报告 JSON 结构保持稳定以支持后端自动化解析。

### 对后端的建议

**1. 字段统一** — `seeds[].url`（接口 2）和 `update_seed_status` 的 `url`（接口 3）使用 URL 字符串作为主键。建议后端确保 URL 在所有接口中采用一致的去参/去 fragment/去尾斜杠规范化，避免同一页面因 URL 微小差异被识别为不同实体。

**2. 接口 5（pagesnapshot）字段设计** — 当前 `markdown` 字段存储 Markdown 内容，文档注释中提到"目前可存 HTML"。建议明确字段语义：`html` 存原始 HTML，`markdown` 存转换后的 Markdown，`content_text`（可选）存纯文本摘要。

**3. 批量上传** — 图片上传是爬虫的吞吐瓶颈之一（每页可能有数十张图）。建议提供批量接口（一次请求上传多张 base64 图片），减少 HTTP 往返开销。

**4. 健康检查** — 建议后端暴露 `GET /api/health/` 端点，Worker 启动时先检测后端可用性再进入轮询循环，避免启动即失败。
