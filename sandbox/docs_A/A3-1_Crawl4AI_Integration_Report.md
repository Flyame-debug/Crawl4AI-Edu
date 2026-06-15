# A3-1 Crawl4AI 集成与爬虫改造 工作报告

## 任务概述

成员 A，完成 N1-N4 子任务：安装并验证 Crawl4AI，封装转换函数，集成到爬虫流程，实现预览/全量双模式。

## 完成情况

### N1：安装 Crawl4AI 并验证

编写测试脚本 `sandbox/tests/test_crawl4ai.py`，包含两个测试用例。`test_from_url` 从 httpbin.org/html 抓取真实 HTML 并通过 Crawl4AI 转换为 Markdown，输出 3598 字符的有效 Markdown 文本。`test_from_raw_html` 验证了 Crawl4AI 的 `raw:` URL 方案可正确处理内存中的 HTML 字符串，确认 `# Hello World` 标题和链接均正确转换。

运行命令：`python sandbox/tests/test_crawl4ai.py`，两项测试均通过。

### N2：封装 Crawl4AI 调用函数

新增 `sandbox/standalone_crawler/crawl4ai_client.py`，实现 `convert_with_crawl4ai(html: str) -> str` 函数。内部通过 Crawl4AI 的 `AsyncWebCrawler` 配合 `raw:` URL 方案处理 HTML 字符串，设置 30 秒超时。当 Crawl4AI 未安装、超时或返回空结果时，自动降级调用 `html_to_markdown_simple`。

同时新增 `sandbox/standalone_crawler/markdown_converter.py`，实现 `html_to_markdown_simple` 降级函数。该函数先使用 `readability-lxml` 提取页面正文，再通过 `markdownify` 转换为 Markdown。当任一库不可用时，逐级回退至原始 HTML，确保系统在任何情况下都能产生可用输出。

### N3：集成到爬虫流程

修改 `sandbox/standalone_crawler/handlers.py` 中的 `process_page` 函数。在获取 HTML 之后、处理图片之前，调用 `convert_with_crawl4ai(html)` 得到 Markdown。`page_data` 字典新增 `html` 和 `markdown` 两个字段。

本地模式下，`_save_page_locally` 函数同时保存 `.html`（至 `output_dir/html/`）和 `.md`（至 `output_dir/md/`）文件，映射文件 `mapping.txt` 新增 md 路径列。

API 模式下，`save_page_snapshot` 调用同时传递 `markdown` 和 `html` 两个字段。修改 `sandbox/standalone_crawler/api_client.py`，为 `save_page_snapshot` 方法新增可选参数 `html: str | None = None`，在请求 payload 中一并发送。

`sandbox/standalone_crawler/crawler.py` 中 `_run_bfs_crawl` 函数新增 `md/` 目录自动创建逻辑。

运行验证：`python sandbox/run_crawler.py https://httpbin.org/html --depth 1`，成功在 `sandbox/data/html/` 下生成 `.html` 文件，在 `sandbox/data/md/` 下生成对应的 `.md` 文件，Markdown 输出为完整的 Herman Melville 小说段落，内容正确。

### N4：预览/全量任务模式支持

修改 `sandbox/run_crawler.py`，新增命令行参数 `--task-type {preview|full}`（默认 `full`）和 `--preview-limit`（默认 10）。预览模式下自动将输出目录切换为 `sandbox/preview_data/`，并在控制台输出醒目的预览模式提示横幅。

修改 `sandbox/standalone_crawler/crawler.py`，`crawl` 和 `_run_bfs_crawl` 函数均新增 `task_type` 和 `preview_limit` 参数。在 BFS 循环中，预览模式会跟踪已完成页面数，达到上限后停止收集新链接并退出循环。日志中输出中文"预览模式"提示。

运行验证：`python sandbox/run_crawler.py https://httpbin.org/html --task-type preview --preview-limit 3 --depth 2`，控制台正确显示预览模式横幅，数据保存至 `sandbox/preview_data/` 目录（含 `html/`、`md/`、`mapping.txt`），未调用后端 API。

## 新增/修改文件清单

新增文件：

`sandbox/tests/__init__.py`
`sandbox/tests/test_crawl4ai.py`
`sandbox/standalone_crawler/crawl4ai_client.py`
`sandbox/standalone_crawler/markdown_converter.py`

修改文件：

`sandbox/standalone_crawler/handlers.py` — 集成 Crawl4AI 转换，双文件保存
`sandbox/standalone_crawler/crawler.py` — 预览/全量模式支持，md 目录创建
`sandbox/standalone_crawler/api_client.py` — save_page_snapshot 新增 html 参数
`sandbox/run_crawler.py` — 新增 --task-type / --preview-limit 参数
`sandbox/requirements.txt` — 新增 crawl4ai, readability-lxml, markdownify 依赖

## 测试结果

N1 测试：`test_crawl4ai.py` 两项测试通过，Markdown 输出分别为 3598 字符和 147 字符，均为有效文本。
N2 测试：`crawl4ai_client.py` smoke test 通过，输出 86 字符 Markdown，标题和代码块正确渲染。`markdown_converter.py` smoke test 通过，输出 78 字符 Markdown。
N3 集成测试：完整爬取 httpbin.org/html，生成 `.html` (3754 bytes) 和 `.md` (3602 bytes) 文件，内容正确。
N4 预览测试：预览模式横幅正确显示，数据写入 `sandbox/preview_data/`，未调用 API。

小主贵安
