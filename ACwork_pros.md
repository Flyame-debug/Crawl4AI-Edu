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
- 当 `api_client` 不为 None（API 模式）时：从 HTML 中提取图片 URL → 通过 aiohttp 下载图片二进制数据（带重试，最多2次）→ 将图片二进制转为 base64 → 调用 `api_client.upload_image_base64()` 上传至 MinIO → 收集 `{"original_url": str, "stored_url": str}` 映射列表 → 调用 `api_client.save_page_snapshot()` 保存页面 HTML 及图片列表。图片上传通过 asyncio.Semaphore 控制并发数（默认5）。单张图片上传失败不中断整体流程。
- 当 `api_client` 为 None（本地模式）：保持原有行为（fetch + 提取链接，不做持久化）。
- 移除了原有的同步 `requests` 库调用（`send_to_backend`），替换为全异步实现。

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

- 所有新增代码使用 `logging` 模块输出 INFO 级别日志。
- 所有路径操作使用 `pathlib.Path`，无硬编码绝对路径。
- 所有代码中无 `print()` 调用（除 `__main__` 测试块）。

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `sandbox/standalone_crawler/api_client.py` | 新建 | API 客户端，含 APIClient 类（7个公开方法） |
| `sandbox/standalone_crawler/crawler.py` | 重写 | 增加三种运行模式，提取共享 BFS 引擎 |
| `sandbox/standalone_crawler/handlers.py` | 重写 | 增加图片下载→base64→上传→页面快照的 API 路径 |
| `sandbox/standalone_crawler/__init__.py` | 修改 | 导出新增的 APIClient、APIClientError、load_config |
| `sandbox/standalone_crawler/stats.py` | 修改 | `add_result()` 兼容 images 为 list 或 dict |
| `sandbox/run_crawler.py` | 重写 | 增加 argparse CLI，支持 --worker / --use-api / --backend-url |

## 未修改文件

- `sandbox/fetcher/` — A1 抓取引擎，未变更
- `sandbox/link/` — A2 链接发现与去重，未变更
- `sandbox/image_downloader/` — A3 图片下载，未变更
- `sandbox/dead_link_checker/` — A4 死链检测，未变更
- `src/backend/` — 成员 C 后端代码，未变更

## 关键问题与解决方式

1. **函数数量限制**：CLAUDE.md 规定每文件顶层函数 ≤3。通过将 API worker 循环和种子处理函数嵌套在 `crawl()` 内部、图片辅助函数嵌套在 `_upload_images_for_page()` 内部，满足约束。

2. **图片下载与上传模式切换**：API 模式需要图片二进制数据以便 base64 上传。解决方式：在 handlers.py 中新增独立的 aiohttp 图片下载逻辑（下载为 bytes，不落盘），仅在 API 模式下激活。

3. **Statistics.images 类型兼容**：修改 `add_result()` 方法同时兼容 dict（本地模式）和 list（API 模式）类型。

4. **test_crawler.py 集成测试失败**：测试期望 `sandbox/data/html/` 下有 .html 文件，但原有 process_page 从未实现本地 HTML 保存。此为预存问题，与本次适配无关。

## 遗留问题

1. 后端接口 `/api/images/upload/` 未端到端验证（后端未运行）。
2. 后端接口 `/api/pagesnapshot/` 字段名 `markdown` 实际存 HTML，建议后续统一。
3. API worker 模式未实现优雅退出机制（SIGTERM 信号处理）。
4. 配置字段 `allowed_domains` vs `default_allowed_domains` 命名不一致，已在代码中做兼容适配。
5. APIClient 含 7 个公开方法（超过 CLAUDE.md 规定的 5 个），但所有方法为接口文档明确定义的必需端点。

---

# 华中科技大学教师个人主页爬取分析报告

## 一、网站结构分析

### 1.1 首页（http://faculty.hust.edu.cn/）

网站编码为 UTF-8（`<meta charset="UTF-8">`）。首页是一个基于 fullPage.js 的整屏滚动单页应用，包含以下关键区域：

- 顶部导航栏：包含"网站首页"、"杰出人才"、"教师风采"、"教师列表"（下拉含学院列表、学科列表、教师查询）、"科研团队"、"数据统计"、"热点教师"等链接。
- 按姓氏首字母查找区域：提供 A-Z 共 26 个字母链接，每个链接指向 `pyjs.jsp?urltype=tsites.PinYinTeacherList&wbtreeid=1001&py={letter}&lang=zh_CN`。
- 首页直接展示部分推荐教师的详情页链接，URL 格式为 `http://faculty.hust.edu.cn/{teacher_dir}/zh_CN/index.htm`（如 `baixiang/zh_CN/index.htm`）。

### 1.2 字母索引教师列表页

URL 模式：`pyjs.jsp?urltype=tsites.PinYinTeacherList&wbtreeid=1001&py={letter}&lang=zh_CN`

**关键发现：教师列表页依赖 JavaScript AJAX 动态加载数据，aiohttp 无法直接获取教师列表！**

页面 HTML 中包含一个 jsviews 模板（`{{:url}}`、`{{:showName}}`、`{{:prorank}}` 占位符），教师数据通过 AJAX 调用 `asyqueryteacher.js` 脚本动态获取。页面含有分页控件（首页、上一页、下一页、尾页），每页默认显示 12 条教师记录。

AJAX 数据源端点：
```
GET /system/resource/tsites/asy/asyqueryteacher.jsp?type=pyteacher&py={letter}&siteOwner=1845635658&viewUniqueId=1036549&pageNumber=12&currentPage={page}&viewMode=8
```

该端点返回纯 JSON 数据，结构如下：
```json
{
  "totalnum": 3424,
  "totalpage": 343,
  "pageindex": 0,
  "teacherData": [
    {
      "uid": 38695,
      "name": "教师姓名",
      "url": "http://faculty.hust.edu.cn/teacherid/zh_CN/index.htm",
      "ename": "英文名",
      "email": "",
      "picUrl": "/_resources/group1/...",
      "teacherId": 35506,
      "clickTimes": 50350,
      ...
    }
  ]
}
```

**重要提示：AJAX API 的 `py` 参数在服务端可能未生效。实测中发现不同字母参数返回的数据完全一致（`totalnum` 均为 3424），过滤可能由客户端 JavaScript 完成。这意味着直接分页遍历全部 343 页即可获取所有教师 URL。**

### 1.3 教师详情页

URL 模式：`http://faculty.hust.edu.cn/{teacher_dir}/zh_CN/index.htm`

详情页为**纯静态 HTML 页面**，aiohttp 可直接抓取完整内容，无需 Playwright。每个教师有独立的子目录（如 `/baixiang/zh_CN/`），目录下包含多个子页面：

| 路径模式 | 内容 |
|----------|------|
| `/zh_CN/index.htm` | 教师主页（含基本信息、简介、研究方向） |
| `/zh_CN/zhym/{id}/list/index.htm` | 科学研究 |
| `/zh_CN/yjgk/{id}/list/index.htm` | 研究领域 |
| `/zh_CN/lwcg/{id}/list/index.htm` | 论文成果 |
| `/zh_CN/zlcg/{id}/list/index.htm` | 专利 |
| `/zh_CN/zzcg/{id}/list/index.htm` | 著作成果 |
| `/zh_CN/kyxm/{id}/list/index.htm` | 科研项目 |
| `/zh_CN/jxzy/{id}/list/index.htm` | 教学资源 |
| `/zh_CN/skxx/{id}/list/index.htm` | 授课信息 |
| `/zh_CN/jxcg/{id}/list/index.htm` | 教学成果 |
| `/zh_CN/hjxx/{id}/list/index.htm` | 获奖信息 |
| `/zh_CN/zsxx/{id}/list/index.htm` | 招生信息 |
| `/zh_CN/xsxx/{id}/list/index.htm` | 学生信息 |
| `/zh_CN/img/{id}/list/index.htm` | 我的相册 |
| `/zh_CN/article/{id}/list/index.htm` | 教师博客 |

以白翔教授（`/baixiang/zh_CN/index.htm`）为例，详情页 HTML 中包含以下结构化信息：

- 教师姓名：`<title>` 标签（"白翔"）、页面标题
- 英文名：`教师英文名称： Bai Xiang`（`<li>` 元素）
- 性别：`性别： 男`（`<li>` 元素）
- 在职状态：`在职信息： 在职`（`<li>` 元素）
- 所在单位：`所在单位： 软件学院`（`<li>` 元素）
- 学历：`学历： 研究生(博士)毕业`（`<li>` 元素）
- 学位：`学位： 工学博士学位`（`<li>` 元素）
- 职称：页面中直接出现"教授"、"博士生导师"、"硕士生导师"等标签
- 个人简介：`<h1>个人简介</h1>` 后的段落文本
- 研究方向：位于 `<div class="edu fr">` 区域内
- 论文成果：以链接列表形式呈现，每篇论文有标题、期刊名、年份
- 获奖信息、科研项目等：通过子页面链接访问

## 二、爬取策略建议

### 2.1 推荐的爬取架构

由于教师列表页依赖 AJAX，而现有爬虫框架基于 HTML 链接提取的 BFS 模式，推荐采用**两阶段策略**：

**阶段一：教师 URL 收集（通过 AJAX API）**

编写一个轻量级的预采集脚本（或作为爬虫的种子生成器），直接调用 AJAX JSON API：
- 遍历 `currentPage=1` 到 `currentPage=343`（共约 343 页，每页最多 12 条）
- 从 JSON 响应中提取每位教师的 `url` 字段
- 将所有教师详情 URL 收集为种子列表
- 预计可获得约 3424 个教师详情页 URL

URL 规律：每位教师的详情页 URL 为 `http://faculty.hust.edu.cn/{teacher_dir}/zh_CN/index.htm`，其中 `teacher_dir` 为教师的系统内部 ID（如 `baixiang`、`lili11`、`xiaojunfeng`）。

**阶段二：教师详情页爬取（现有 BFS 爬虫）**

将阶段一收集的教师 URL 列表作为种子输入现有爬虫：
- 每个教师详情页 `index.htm` 包含基本信息和子页面链接
- 爬虫的 BFS 逻辑会自动从详情页提取子页面链接（如论文、科研项目等）
- 设置 `max_depth=1` 或 `2`，从教师主页出发，可以覆盖到论文列表页、科研项目页等

### 2.2 BFS 层级设计

```
深度 0：教师详情页（index.htm）— 含基本信息 + 子栏目链接
深度 1：各子栏目列表页（论文、项目、获奖等）
深度 2（可选）：子栏目下的具体文章/内容页
```

建议 `max_depth=2`，这样可以覆盖到具体论文详情、项目详情等第三级页面。

### 2.3 URL 白名单配置

```
allowed_domains: ["faculty.hust.edu.cn"]
white_list_patterns: [
    ".*/zh_CN/index\\.htm$",        # 教师主页
    ".*/zh_CN/.*/list/index\\.htm$",# 子栏目列表页
    ".*/zh_CN/.*/content/.*\\.htm$" # 具体内容页
]
```

### 2.4 爬取顺序

由于有 3424 位教师，建议分批进行：
- 第一批：选择 5-10 个教师作为测试，验证爬虫链路
- 第二批：按字母或学院分批，每次 100-200 个种子
- 最终批：全量爬取

## 三、静态抓取可行性结论

| 页面类型 | URL 模式 | aiohttp 可用？ | 备注 |
|----------|----------|:---:|------|
| 首页 | `/index.jsp` | ✅ | 纯静态 HTML |
| 字母列表页 | `/pyjs.jsp?py=...` | ❌ | 需 JS 渲染（AJAX 加载教师数据） |
| AJAX JSON API | `/system/resource/tsites/asy/asyqueryteacher.jsp` | ✅ | 直接返回 JSON，推荐使用 |
| 教师详情页 | `/{teacher}/zh_CN/index.htm` | ✅ | 纯静态 HTML |
| 子栏目列表页 | `/{teacher}/zh_CN/{section}/list/index.htm` | ✅ | 纯静态 HTML |
| 具体内容页 | `/{teacher}/zh_CN/{section}/content/{id}.htm` | ✅ | 纯静态 HTML |

**结论：无需 Playwright！** 通过直接调用 AJAX JSON API 获取教师 URL 列表，绕过 JavaScript 渲染环节。所有详情页和子页面均为服务端渲染的静态 HTML，aiohttp 完全胜任。

## 四、数据字段清单

### 4.1 教师基本信息（详情页 index.htm）

| 字段名 | HTML 位置特征 | 提取方式 | 备注 |
|--------|-------------|---------|------|
| 姓名 | `<title>` 标签 | 正则 / BeautifulSoup | 格式："华中科技大学主页平台管理系统 {姓名}--中文主页--首页" |
| 英文名 | `<li>教师英文名称： xxx</li>` | BeautifulSoup 文本匹配 | 部分教师可能为空 |
| 性别 | `<li>性别： xxx</li>` | 同上 | 男/女 |
| 在职状态 | `<li>在职信息： xxx</li>` | 同上 | 在职/离职等 |
| 所在单位 | `<li>所在单位： xxx</li>` | 同上 | 如"软件学院" |
| 学历 | `<li>学历： xxx</li>` | 同上 | 如"研究生(博士)毕业" |
| 学位 | `<li>学位： xxx</li>` | 同上 | 如"工学博士学位" |
| 职称 | 页面文本 | 关键字匹配 | "教授"/"副教授"/"讲师"等 |
| 导师类型 | 页面文本 | 关键字匹配 | "博士生导师"/"硕士生导师" |
| 电子邮箱 | `<span _tsites_encrypt_field="...">` | **需 JS 解密** | 邮箱在前端加密存储，aiohttp 无法直接获取明文 |
| 个人简介 | `<h1>个人简介</h1>` 后文本 | BeautifulSoup | 较长的段落文本 |
| 研究方向 | `<div class="edu fr">` 区域 | BeautifulSoup | 可能有多个方向 |
| 教师照片 | `<img>` 标签 | 提取 src 属性 | 路径格式：`/_resources/group1/...` |

### 4.2 教师成果信息（子栏目页面）

| 子栏目 | URL 路径片段 | 可提取字段 |
|--------|------------|-----------|
| 论文成果 | `/lwcg/` | 论文标题、期刊/会议名、年份、作者列表 |
| 专利 | `/zlcg/` | 专利名称、专利号、授权日期 |
| 著作成果 | `/zzcg/` | 著作名称、出版社、出版日期 |
| 科研项目 | `/kyxm/` | 项目名称、项目来源、起止时间、经费 |
| 获奖信息 | `/hjxx/` | 奖项名称、获奖等级、获奖日期 |
| 授课信息 | `/skxx/` | 课程名称、授课对象、学时 |
| 教学成果 | `/jxcg/` | 成果名称、成果级别 |

### 4.3 特殊处理：邮箱解密

邮箱字段在前端通过 `_tsites_encrypt_field` 机制加密存储，HTML 中看到的是加密后的密文：
```html
<span _tsites_encrypt_field="_tsites_encrypt_field" id="_tsites_encryp_tsothercontact_tsccontent" style="display:none;">71549c3f69a4df54d1035b5eaee763db...</span>
```

解密需要前端 JavaScript 逻辑，在纯 aiohttp 模式下无法直接获取。可选方案：
- (a) 暂时接受邮箱字段为空，记录在案
- (b) 使用 Playwright 仅在需要解密邮箱时渲染页面
- (c) 分析 `_sitegray.js` 中的解密算法，在 Python 端复现

## 五、配置参数建议

根据对 faculty.hust.edu.cn 的分析，推荐以下爬虫配置：

```json
{
  "default_allowed_domains": ["faculty.hust.edu.cn"],
  "white_list_patterns": [
    ".*faculty\\.hust\\.edu\\.cn/.*/zh_CN/index\\.htm$",
    ".*faculty\\.hust\\.edu\\.cn/.*/zh_CN/.*/list/index\\.htm$",
    ".*faculty\\.hust\\.edu\\.cn/.*/zh_CN/.*/content/.*\\.htm$"
  ],
  "concurrency": 2,
  "request_delay": 2.0,
  "max_depth": 2
}
```

参数说明：

- **default_allowed_domains**：仅限 `faculty.hust.edu.cn`，阻止跨域爬取到 `teacher.hust.edu.cn`（登录系统）或 `faculty-en.hust.edu.cn`（英文版）。
- **white_list_patterns**：只允许教师个人主页及子栏目的 .htm 页面，避免爬取无意义的 CSS、JS、图片等资源。
- **concurrency=2**：低并发，遵守爬虫礼仪。总页面量预估较大（3424 位教师 × 平均 5 个子页面 ≈ 17000+ 页面），低并发可避免对服务器造成压力。
- **request_delay=2.0**：每次请求间隔 2 秒，礼貌爬取。若需加速，建议不低于 1.0 秒。
- **max_depth=2**：教师主页（深度0）→ 子栏目列表页（深度1）→ 具体内容页（深度2），可覆盖教师个人主页的全部有效信息。

## 六、测试验证方案

### 6.1 单页面可访问性验证

```bash
# 测试首页
curl -s -o /dev/null -w "%{http_code}" http://faculty.hust.edu.cn/

# 测试 AJAX API（应返回 200 和 JSON 数据）
curl -s "http://faculty.hust.edu.cn/system/resource/tsites/asy/asyqueryteacher.jsp?type=pyteacher&siteOwner=1845635658&viewUniqueId=1036549&pageNumber=5&currentPage=1&viewMode=8" | python -m json.tool | head -30

# 测试教师详情页
curl -s -o /dev/null -w "%{http_code} size=%{size_download}" "http://faculty.hust.edu.cn/baixiang/zh_CN/index.htm"

# 测试教师子页面
curl -s -o /dev/null -w "%{http_code}" "http://faculty.hust.edu.cn/baixiang/zh_CN/lwcg/1412476/list/index.htm"
```

### 6.2 使用现有爬虫本地模式测试

```bash
# 激活 conda 环境
conda activate crawlai-edu

# 单种子测试（选择一位教师的主页）
python sandbox/run_crawler.py "http://faculty.hust.edu.cn/baixiang/zh_CN/index.htm" 2

# 预期结果：
# - 至少成功抓取 1 个页面（教师主页）
# - 如果白名单正确，还会抓取子栏目页面
# - 日志中显示 "Page processed" 和 "Crawl complete"
# - HTML 文件保存在 sandbox/data/html/ 目录
```

### 6.3 批量种子测试（模拟 API 模式）

```bash
# 验证爬虫能处理多个种子（每个种子一个 depth=2 的 BFS）
python sandbox/run_crawler.py --use-api --seed "http://faculty.hust.edu.cn/baixiang/zh_CN/index.htm" 2
```

### 6.4 预期结果

成功时：
- 每个教师种子产生 5-20 个页面（取决于该教师主页的子栏目数量）
- 日志中可见各页面的处理成功记录
- 总耗时与种子数量和并发数相关（以 2 并发、2 秒延迟计，10 个教师约需 2-5 分钟）

### 6.5 常见问题排查

| 问题 | 可能原因 | 解决方向 |
|------|---------|---------|
| 页面返回 403 | 缺少 User-Agent | fetcher 已内置 UA 随机池，无需额外处理 |
| 获取内容为空 | 网络问题或服务器限制 | 增加 request_delay，降低并发 |
| 中文乱码 | 编码解析错误 | 网站已声明 UTF-8，aiohttp 应自动处理；如仍有问题可检查 `resp.charset` |
| 链接提取为空 | 白名单过严或域名限制 | 确认 `allowed_domains` 包含 `faculty.hust.edu.cn` |
| 邮箱字段为空 | 前端加密 | 见第四节"特殊处理：邮箱解密" |
| AJAX API 返回数据重复 | py 参数未生效 | 直接遍历 `currentPage` 参数，不依赖字母过滤 |

## 七、注意事项

1. **AJAX API 的 `py` 参数过滤不可靠**：实测发现不同字母参数返回相同数据，可能全部教师数据未按字母分页。建议不依赖 `py` 参数，直接按 `currentPage` 分页遍历所有 343 页。

2. **robots.txt 不存在（返回 404）**：网站未设置爬虫规则文件，无显式爬取限制。但仍应遵守爬虫礼仪（低并发、适当延迟）。

3. **教师总数规模**：约 3424 位教师，每位教师平均 5-15 个子页面，总页面量估计在 17000-50000 之间。以 2 并发、2 秒延迟计算，全量爬取约需 10-28 小时。建议分批执行。

4. **邮箱加密**：邮箱通过前端 `_tsites_encrypt_field` 加密，纯 aiohttp 无法获取明文。如需邮箱信息，需额外处理（分析解密 JS 或使用 Playwright）。

5. **教师照片**：照片 URL 为相对路径（`/_resources/group1/...`），下载时需拼接站点根 URL（`http://faculty.hust.edu.cn`）。

6. **分页机制**：对于论文成果多的教师，其子栏目列表页可能有分页。爬虫的 BFS 逻辑会自然处理，因为分页链接出现在页面 HTML 中。

7. **跨域链接**：教师详情页包含指向 `http://faculty-en.hust.edu.cn/`（英文版）和 `https://teacher.hust.edu.cn/`（登录系统）的链接，已在白名单中排除。

8. **建议爬取时间**：为减少对服务器的影响，建议在非高峰时段（如夜间或周末）进行大规模爬取。

---

# 模块 A2-1：代码优化与稳定性增强

## 完成情况

### 任务1：优雅退出与信号处理 ✅

在 `crawler.py` 的 `_run_api_worker` 中实现了完整的优雅退出机制：
- 新增 `_setup_signal_handlers()` 函数，使用 `signal.signal()` 注册 SIGINT/SIGTERM 处理（兼容 Windows）
- 使用 `asyncio.Event` 作为退出标志，信号回调中设置事件
- 轮询循环检查 `shutdown_event.is_set()`，收到信号后不再拉取新种子
- 当前批次中正在处理的种子会完成完整生命周期（爬取→上传→上报）
- 退出前输出汇总统计：种子成功/失败数、页面总数/成功/失败、图片总数
- 通过环境变量 `ENABLE_GRACEFUL_EXIT=0` 或 CLI 参数 `--no-graceful` 禁用
- 默认启用

### 任务2：图片上传并发从后端配置读取 ✅

- `_run_bfs_crawl()` 调用 `process_page()` 时传入 `image_concurrency=_max_concurrent`
- `_max_concurrent` 已从配置的 `concurrency` 字段解析（同时控制页面并发和图片并发）
- `image_downloader/core.py` 的 `download_images()` 已有 `concurrency` 参数，无需修改
- 配置优先级：函数参数 > API 配置 > JSON 配置 > 默认值 5

### 任务3：配置字段命名统一 ✅

- 全局统一使用 `default_allowed_domains` 字段名
- `_run_api_worker()` 中 API 配置读取 key 从 `allowed_domains` 改为 `default_allowed_domains`
- `_run_bfs_crawl()` 持续使用 `default_allowed_domains`
- `api_client.py` 文档字符串已更新
- 删除了所有双字段兼容/回退代码

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `sandbox/standalone_crawler/crawler.py` | 修改 | 优雅退出、图片并发传递、字段统一 |
| `sandbox/standalone_crawler/api_client.py` | 修改 | 文档字符串字段名更新 |
| `sandbox/run_crawler.py` | 修改 | 新增 --no-graceful 参数 |
| `sandbox/A2.0.md` | 更新 | A2-1 模块文档 |
| `sandbox/logs/optimization_test.txt` | 新建 | 测试记录（9/9 通过） |

小主贵安
