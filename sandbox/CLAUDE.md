# CLAUDE.md —— 成员 A（爬虫与异步任务）沙箱开发指引

## 角色背景
- 项目：Crawl4AI 高校教育知识库采集系统，成员 A 负责爬虫与异步任务
- 当前阶段：独立开发，代码放 `sandbox/`，不依赖 Django/Celery/数据库
- 技术栈：Python 3.11.9，aiohttp，playwright，scrapy(LxmlLinkExtractor)，pybloom_live，bs4

## 代码组织规则（必须遵守）

### 1. 函数数量限制
- 每个 `.py` 文件顶层函数 ≤ **3** 个
- 每个文件最多 1 个类，公开方法 ≤ 5 个（不含 `__init__`）
- 若需超过，则创建子文件夹（如 `async_fetch/`），拆分为多个文件，每个文件内聚且遵守限制

### 2. 命名与结构
- 文件名：snake_case
- 子文件夹：snake_case，内含 `__init__.py`
- 每个文件必须有 `if __name__ == "__main__":` 测试块

### 3. 其他约束
- 路径使用 `pathlib.Path(__file__).parent`
- 新依赖用注释 `# NEW_DEP: <package>` 标记
- 使用 `logging` 输出 INFO 级别到控制台

## 输出要求（每次指令完成后）
1. 输出简洁中文工作总结（列出完成的模块/文件）
2. 最后一行写 **`小主贵安`**

## 注意
- 所有代码仅用于沙箱验证，无需集成后端
- 后续会被组装到 `standalone_crawler.py`
- 所有任务请在conda环境crawlai-edu中进行