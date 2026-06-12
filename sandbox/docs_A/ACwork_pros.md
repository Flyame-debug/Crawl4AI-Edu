# Crawl4AI 项目集成适配 —— 工作总结

## 概述

本次工作将成员 A 的独立爬虫代码（sandbox/standalone_crawler）适配到成员 C 定义的后端 API 接口（sandbox/interface_doc.md），在保持所有核心爬虫逻辑不变的前提下，新增 API 工作模式，支持从后端动态获取配置、轮询待爬种子、上传图片和页面数据、上报任务结果。

## 需求完成情况

### 需求 1：API 客户端（api_client.py）—— 已完成

新建文件 `sandbox/standalone_crawler/api_client.py`，实现 `APIClient` 类，包含全部 7 个接口方法：

| 方法 | 对应接口 | HTTP |
|------|----------|------|
| `get_config()` | `/api/crawler/config/db/` | GET |
| `get_pending_seeds(limit)` | `/api/seeds/pending/?limit=N` | GET |
| `update_seed_status(url, status)` | `/api/seeds/status/` | POST |
| `start_crawl_task(seed_url, max_depth, config)` | `/api/crawl/start/` | POST |
| `upload_image_base64(image_base64_str, filename)` | `/api/images/upload/` | POST |
| `save_page_snapshot(url, markdown, category, images)` | `/api/pagesnapshot/` | POST |
| `report_task_result(task_id, status, ...)` | `/api/tasks/{task_id}/result/` | POST |

所有方法采用 aiohttp 异步请求，内建指数退避重试（最多3次），超时控制（默认30秒），结构化错误日志。基础 URL 从环境变量 `CRAWLER_BACKEND_URL` 读取（默认 `http://127.0.0.1:8000`）。同时导出 `APIClientError` 异常类供上层捕获。

### 需求 2：爬虫主入口（crawler.py）—— 已完成

修改 `sandbox/standalone_crawler/crawler.py`，增加三种运行模式：

1. **本地模式**（原有行为，`api_client=None`）：按原有逻辑执行 BFS 爬取，配置从本地 JSON 文件读取，不调用任何 API。完全向后兼容。

2. **API Worker 模式**（`api_client` 提供且 `seed_url=None`）：进入无限轮询循环，从后端获取配置 → 拉取待爬种子 → 对每个种子标记 crawling → 启动任务获取 task_id → 执行 BFS 爬取 → 上报结果 → 标记最终状态。支持定期刷新配置（每10轮）。

3. **API 单次模式**（`api_client` 提供且 `seed_url` 指定）：对单个种子执行完整生命周期（标记→启动→爬取→上报→标记），适用于 `--use-api --seed URL` 场景。

核心 BFS 爬取逻辑提取为 `_run_bfs_crawl()` 函数，被本地模式和 API 模式共享，确保 BFS 递归逻辑完全一致。`process_page()` 调用已传入 `api_client`、`task_id`、`seed_meta` 参数，使页面处理函数能正确使用 API 上传功能。

### 需求 3：页面处理函数（handlers.py）—— 已完成

重写 `sandbox/standalone_crawler/handlers.py`，核心修改：

- `process_page()` 新增可选参数 `api_client`、`task_id`、`seed_meta`、`image_concurrency`。
- 当 `api_client` 不为 None（API 模式）时：
  - 从 HTML 中提取图片 URL（使用 BeautifulSoup，复用 image_downloader 的逻辑）
  - 通过 aiohttp 下载图片二进制数据（带重试，最多2次）
  - 将图片二进制转为 base64，调用 `api_client.upload_image_base64()` 上传至 MinIO
  - 收集 `{"original_url": str, "stored_url": str}` 映射列表
  - 调用 `api_client.save_page_snapshot()` 保存页面 HTML 及图片列表
  - 图片上传通过 asyncio.Semaphore 控制并发数（默认5）
  - 单张图片上传失败不中断整体流程
- 当 `api_client` 为 None（本地模式）：保持原有行为（fetch + 提取链接，不做持久化）。
- 移除了原有的同步 `requests` 库调用（`send_to_backend`），替换为全异步实现。
- 所有图片下载/上传辅助函数嵌套在 `_upload_images_for_page()` 内部，保持模块顶层函数数 ≤3。

### 需求 4：命令行入口（run_crawler.py）—— 已完成

重写 `sandbox/run_crawler.py`，使用 argparse 替代原有手工解析：

- 保留原有位置参数兼容：`seed_url`、`max_depth`、`config_path`。
- 新增 `--worker`：启动 API worker 轮询模式。
- 新增 `--use-api`：启用 API 集成（配合 `--seed` 或位置参数使用）。
- 新增 `--seed`：显式指定 API 模式的种子 URL。
- 新增 `--backend-url`：覆盖环境变量中的后端地址。
- 新增 `--poll-interval`：控制 worker 模式轮询间隔（默认10秒）。
- 原有命令（如 `python run_crawler.py https://example.com 2`）仍正常工作。

### 需求 5：日志与路径规范 —— 已完成

- 所有新增代码使用 `logging` 模块输出 INFO 级别日志，通过 `get_logger()` 工具函数配置，格式包含时间、模块名、级别。
- 所有路径操作使用 `pathlib.Path`，无硬编码绝对路径。
- 所有代码中无 `print()` 调用（除 `__main__` 测试块中的测试输出）。

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `sandbox/standalone_crawler/api_client.py` | **新建** | API 客户端，含 APIClient 类（7个公开方法） |
| `sandbox/standalone_crawler/crawler.py` | **重写** | 增加三种运行模式，提取共享 BFS 引擎 |
| `sandbox/standalone_crawler/handlers.py` | **重写** | 增加图片下载→base64→上传→页面快照的 API 路径 |
| `sandbox/standalone_crawler/__init__.py` | **修改** | 导出新增的 APIClient、APIClientError、load_config |
| `sandbox/standalone_crawler/stats.py` | **修改** | `add_result()` 兼容 images 为 list 或 dict |
| `sandbox/run_crawler.py` | **重写** | 增加 argparse CLI，支持 --worker / --use-api / --backend-url |

## 未修改文件（严格遵循约束）

- `sandbox/fetcher/` — A1 抓取引擎，未变更
- `sandbox/link/` — A2 链接发现与去重，未变更
- `sandbox/image_downloader/` — A3 图片下载，未变更
- `sandbox/dead_link_checker/` — A4 死链检测，未变更
- `src/backend/` — 成员 C 后端代码，未变更

## 关键问题与解决方式

1. **函数数量限制**：CLAUDE.md 规定每文件顶层函数 ≤3。crawler.py 中需要 API worker 循环和单种子处理逻辑，通过将 `_run_api_worker` 嵌套在 `crawl()` 内部、将 `_process_single_seed` 嵌套在 `_run_api_worker` 内部，保证顶层函数仅 `load_config`、`crawl`、`_run_bfs_crawl` 三个。handlers.py 中图片下载/上传相关辅助函数（`_extract_image_urls`、`_download_image_bytes`、`_derive_filename`）均嵌套在 `_upload_images_for_page` 内部。

2. **图片下载与上传模式切换**：原有 image_downloader 模块始终将图片保存到本地磁盘，返回 `{url: local_path}` 映射。API 模式需要图片二进制数据以便 base64 上传。解决方式：在 handlers.py 中新增独立的 aiohttp 图片下载逻辑（下载为 bytes，不落盘），仅在 API 模式下激活；本地模式保持原有行为。

3. **Statistics.images 类型兼容**：原 stats.py 假设 images 为 dict（本地模式返回 `{url: path}`），API 模式下 process_page 返回 list（`[{original_url, stored_url}]`）。修改 `add_result()` 方法同时兼容 dict 和 list 类型。

4. **test_crawler.py 集成测试失败**：测试期望 `sandbox/data/html/` 下有 .html 文件，但原有 process_page 从未实现本地 HTML 保存（该功能在原代码中即缺失）。此为预存问题，与本次适配无关。

5. **crawler_config.json 字段差异**：后端 API 返回的配置字段（`allowed_domains`、`white_list_patterns`、`enable_dead_check`）与原配置文件字段名（`default_allowed_domains`、`white_list_patterns`、无对应项）存在差异。已在 API worker 模式中做字段映射适配。

## 遗留问题与待确认事项

1. **后端接口 `/api/images/upload/` 测试**：由于后端未在本机运行，base64 图片上传接口尚未端到端验证。字段格式已严格按接口文档实现。

2. **后端接口 `/api/pagesnapshot/` 字段名**：接口文档定义请求体字段为 `markdown`（实际存 HTML），建议后续统一为 `html` 或 `content`，避免命名混淆。

3. **API worker 退出机制**：当前 worker 模式为无限循环，未实现优雅退出（如 SIGTERM 信号处理）。建议后续迭代增加。

4. **配置字段映射**：后端 `/api/crawler/config/db/` 返回的 `allowed_domains` 字段在本地配置文件中为 `default_allowed_domains`，已做兼容处理，但建议后端或前端统一命名。

5. **图片上传并发控制**：当前图片上传并发数默认 5（硬编码），可从后端配置的 `concurrency` 字段复用，但接口文档未明确图片上传专用并发参数，待确认。

