# Crawl4AI 项目 交付物查询清单 1

## 成员 A 下属 A2-2 模块交付

本清单记录模块 A2-2（实战爬取 – 华中科技大学教师全量抓取）的所有交付物，供成员 B（AI 处理）和成员 D（前端展示）使用。

### 核心数据交付

| 序号 | 交付物名称 | 内容说明 | 地址 |
|------|-----------|---------|------|
| 1 | HUST 教师数据压缩包 | 12813 个 HTML 页面 + 1323 张图片 + 映射文件 + 索引 JSON | `hust_faculty_data.tar.gz`（项目根目录，356MB） |
| 2 | 数据索引文件 | URL → HTML 路径 + 图片路径 + 深度的 JSON 映射，共 12813 条记录 | `sandbox/data/metadata.json` |
| 3 | URL 映射文件 | 爬虫实时记录的 URL → 文件路径映射（供索引脚本消费） | `sandbox/data/mapping.txt` |
| 4 | HTML 页面目录 | 教师主页及子栏目页面（MD5 哈希命名） | `sandbox/data/html/`（12813 个文件） |
| 5 | 图片目录 | 教师头像及页面图片（MD5 哈希命名） | `sandbox/data/images/`（1323 个文件） |

### 脚本与配置交付

| 序号 | 交付物名称 | 内容说明 | 地址 |
|------|-----------|---------|------|
| 6 | 种子生成脚本 | 调用 HUST AJAX API 生成 3350 个教师主页 URL | `sandbox/seed_generators/generate_faculty_seeds.py` |
| 7 | 全量种子文件 | 3350 个教师主页 URL（无重复） | `sandbox/seeds/faculty_seeds.txt` |
| 8 | 种子分片文件 | 5 个批次分片（每批约 670 个 URL） | `sandbox/seeds/faculty_seeds_batch{00..04}.txt` |
| 9 | 试点种子样本 | 前 10 个种子 URL 用于试点验证 | `sandbox/seeds/faculty_seeds_sample.txt` |
| 10 | HUST 高校配置 | allowed_domains、white_list_patterns、延迟/并发参数 | `sandbox/config/schools/hust_faculty.json` |
| 11 | 配置加载模块 | 根据域名自动加载学校配置的 `load_school_config()` 函数 | `sandbox/standalone_crawler/config_loader.py` |
| 12 | 索引生成脚本 | 读取 mapping.txt 生成 metadata.json | `sandbox/scripts/build_metadata.py` |

### 日志与报告交付

| 序号 | 交付物名称 | 内容说明 | 地址 |
|------|-----------|---------|------|
| 13 | 试点抓取报告 | 10 个 URL 试点抓取统计、异常分析、配置建议 | `sandbox/logs/pilot_report.txt` |
| 14 | 全量抓取日志（批次1） | 672 个种子，深度 1，抓取详细过程 | `sandbox/logs/full_crawl_batch1.log` |
| 15 | 全量抓取日志（批次2） | 670 个种子，深度 1，抓取详细过程 | `sandbox/logs/full_crawl_batch2.log` |
| 16 | 全量抓取日志（批次3） | 674 个种子，深度 1，抓取详细过程 | `sandbox/logs/full_crawl_batch3.log` |
| 17 | 全量抓取日志（批次4） | 669 个种子，深度 1，抓取详细过程 | `sandbox/logs/full_crawl_batch4.log` |
| 18 | 全量抓取日志（批次5） | 665 个种子，深度 1，抓取详细过程 | `sandbox/logs/full_crawl_batch5.log` |

### 成员 B（AI 处理）使用指引

从 `hust_faculty_data.tar.gz` 解压后，读取 `sandbox/data/metadata.json` 获取 URL 到文件的映射。每个条目包含 `html`（HTML 文件相对路径）、`images`（图片文件相对路径数组，非空表示包含教师头像）和 `depth`（页面深度，0 为教师主页，1 为子栏目页）。共 12813 条记录中，12791 条包含至少一张图片。

### 成员 D（前端展示）使用指引

前端可通过 metadata.json 中的 URL 字段定位教师页面和头像图片。教师主页（depth=0）包含教师姓名、研究领域、联系方式等核心信息。子栏目页（depth=1）包含论文成果、科研项目、获奖信息等附属内容。图片路径为相对于项目根目录的路径（如 `sandbox/data/images/xxx.png`），前端可据此构建图片访问 URL。

### 抓取策略概要

目标网站：华中科技大学教师主页平台（faculty.hust.edu.cn），请求延迟 2.0 秒，并发数 2，抓取深度 1（教师主页 + 一级子栏目），重试次数 3，成功率约 99%。

---

文档生成日期：2026-06-09
生成模块：A2-2
