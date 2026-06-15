# A 模块与后端接口对接反馈（基于第二版接口文档）

> **文档版本**：基于成员 C 的 `第二版接口文档（面向A,B,D）.md` V2.0
> **审查范围**：`sandbox/standalone_crawler/api_client.py` 全部 7 个方法，及 `crawler.py`、`handlers.py` 中的实际调用点
> **目的**：仅用于向成员 C 反馈对接差异和待确认问题，A 模块将据此调整

---

## 一、对接总体评估

A 模块现有 `APIClient` 实现了 7 个方法，覆盖了 V1 版接口文档的全部端点。与 V2.0 文档对比，发现 **4 处关键不一致**（含 1 处破坏性变更）、**3 个缺失接口**、**6 个待沟通问题**。主要差异集中在统一响应格式包装、字段名变更和新增强制入参三方面。

---

## 二、接口不一致清单

| # | 接口名称 | 文档定义 (V2.0) | 当前 A 模块实现 | 影响评估 | 建议修改方 |
|---|---------|----------------|----------------|---------|-----------|
| 1 | **统一响应格式** | 所有接口返回 `{"code": 200, "msg": "success", "data": {...}}`，业务数据嵌套在 `data` 内 | `_parse_json` 直接返回整个 JSON dict，调用方通过 `resp.get("task_id")`、`data.get("seeds")` 等方式直接取顶层字段 | **致命**：所有 7 个接口的响应解析全部失效。例如 `start_resp.get("task_id")` 将返回 `None`（因为 `task_id` 在 `resp["data"]["task_id"]`） | **C 确认格式；A 适配**：若格式确认，A 需在 `_request` 中统一解包 `data` 字段（并处理 `code != 200` 的错误） |
| 2 | **POST /api/seeds/status/** | 入参改为 `seed_id、status`（V1 为 `url、status`） | 发送 `{"url": url, "status": status}`，其中 `url` 是字符串 | **破坏性变更**：A 模块当前以 URL 字符串作为主键更新状态，未追踪 `seed_id`（整数）。`/api/seeds/pending/` 响应中包含 `id` 字段但 A 未提取存储 | **需沟通**：是否两套参数共存（`url` + `seed_id` 都可），还是强制迁移？若强制迁移，A 需在种子生命周期中携带 `seed_id` |
| 3 | **POST /api/pagesnapshot/** | 新增 `task_type`、`user_prompt`、`task_id` 三个必填字段；HTML 字段名从 `html` 改为 `raw_html` | 发送 `url`、`markdown`、`html`、`category`、`images`；未发送 `task_type`、`user_prompt`、`task_id` | **功能性缺失**：后端内部逻辑依赖 `task_type` 区分预览/正式，依赖 `user_prompt` 通知 B 进入清洗流程。字段名不匹配导致 `raw_html` 在后端为空 | **A 适配**：补充三个新增字段，`html` → `raw_html`。需确认 `category` 和 `images` 是否保留 |
| 4 | **POST /api/crawl/start/** | 新增 `task_type`、`user_prompt`、`ai_model`、`ai_api_url` | 发送 `seed_url`、`max_depth`、`config`；未发送新增四字段 | **功能性缺失**：后端依赖 `task_type` 初始化任务模式、依赖 `user_prompt`/`ai_model` 触发 AI 脚本生成流程 | **A 适配**：补充四个新增字段。需确认原有 `seed_url`、`max_depth`、`config` 是否仍保留 |
| 5 | **POST /api/tasks/{id}/result/** | 入参：`task_id、status、total_pages、success_pages` | 额外发送 `failed_pages`、`report`、`error_message` | **低风险**：多发送字段一般被后端忽略，确认是否接受 | **C 确认**：文档是否漏列了 `failed_pages`、`report`、`error_message` |

---

## 三、缺失接口（文档有但 A 未实现）

| # | 接口名称 | 用途 | 优先级 | 当前状态与备注 |
|---|---------|------|--------|-------------|
| 1 | **POST /api/ai/generate-rules/** | 后端中转 AI 规则生成请求，接收 `ai_model`、`ai_api_url`、`user_prompt`、`html_skeleton`，返回 `rule_content` | **中**（P2） | A 模块已通过本地 `generate_extraction_rules()` 函数实现完整的规则生成能力（Ollama 直连 + 兜底逻辑）。若后端希望中转管理（统一记录、计费、切换模型），则需在 `api_client.py` 新增方法。当前可先保持本地直连模式，P2 阶段再迁移 |
| 2 | **GET /api/crawler/status/** | 爬虫状态查询，对接方 A/D | **低** | A 模块作为状态上报方而非查询方，该接口主要用于 D（前端面板）展示。A 可在启动时调一次用于确认后端可达，非核心依赖 |
| 3 | **GET /api/health/** | 服务健康检查 | **低** | 建议 A 在 Worker 模式启动时增加一次健康检查调用，避免启动后立即因后端不可用而报错。实现成本极低（一行 `requests.get`） |

---

## 四、需要沟通的问题

### 问题 1：统一响应格式的具体约定（高优先级）

文档约定所有接口返回 `{"code": 200, "msg": "success", "data": {...}}`。需确认：

- **错误响应是否也遵循此格式？** 例如 `{"code": 400, "msg": "seed not found", "data": null}`。A 模块的 `_request` 方法需要根据 `code` 判断成功/失败。
- **`code` 的值是否总是 HTTP 状态码？** 还是仅用 200 表示成功、其他整数值表示业务错误码？
- **分页/列表接口的 `data` 结构**：例如 `GET /api/seeds/pending/` 返回的 `data` 是 `{"count": 3, "seeds": [...]}` 还是直接 `{"seeds": [...]}`（总数字段在外层）？

### 问题 2：POST /api/seeds/status/ 的 seed_id 迁移方案

V1 版使用 `url` 字符串标识种子，V2 改为 `seed_id`（整数）。这是一个破坏性变更，需明确：

- A 模块当前在 `crawler.py` 中有 **5 处** `update_seed_status` 调用，均以 URL 字符串传递。若全面迁移到 `seed_id`，A 需要从 `/api/seeds/pending/` 响应中提取 `seed.id`，在整个 Worker 种子生命周期中携带，最后用 `seed_id` 更新状态。
- **是否可保留 `url` 参数作为兼容？** 即 `POST /api/seeds/status/` 同时接受 `{"seed_id": 1}` 和 `{"url": "https://..."}`，后端内部通过 url 反查 seed_id。
- 如果强制 `seed_id`，建议 `/api/seeds/pending/` 响应中 `id` 字段名改为 `seed_id` 以保持命名一致。

### 问题 3：POST /api/pagesnapshot/ 的字段变动确认

V2 文档列出了 `url`、`raw_html`、`markdown`、`task_id`、`task_type`、`user_prompt` 六个字段。需确认：

- **`category` 和 `images` 是否已移除？** V1 版中 A 将图片列表作为 `images` 字段上传（含 `original_url` 和 `stored_url`），并将分类标记为 `category`。若已移除，图片关联需通过其他方式建立；若仍保留，建议文档补充。
- **`raw_html` 与 `html` 的语义**：文档使用 `raw_html` 强调原始 HTML。A 当前也保存原始 HTML（未经任何处理），仅字段名不同。确认是否接受 `html` 作为别名，或必须改为 `raw_html`。

### 问题 4：POST /api/crawl/start/ 的原有字段保留

V2 文档标注"原有接口全部保留，仅增补字段"，但文档中只列出了新增四字段（`task_type`、`user_prompt`、`ai_model`、`ai_api_url`），未列出原有字段。需确认：

- **`seed_url` 是否保留？** A 模块通过此字段指定要爬取的种子 URL。
- **`max_depth` 和 `config` 是否保留？** A 模块通过 `config` 传递 `max_concurrent` 和 `request_delay`。
- 建议文档补充完整入参表（含原有 + 新增）。

### 问题 5：认证机制

V2 文档定义了 `POST /api/auth/login/` 登录接口返回 Token。但所有 A 相关接口均未标注是否需要认证。需确认：

- **A 模块调用后端接口时是否需要携带 Token（如 `Authorization: Bearer <token>`）？** 当前 `api_client.py` 和 `_request` 方法未发送任何认证头。
- 如果需要认证，Worker 模式长期运行时 Token 过期如何处理？是否支持通过环境变量配置长期有效的 API Key？

### 问题 6：task_type 取值对齐

C 文档使用 `preview | formal`，A 模块内部使用 `"preview" | "full"`。两者语义相同但取值不同，需统一：
- A 模块 CLI 参数 `--task-type` 当前接受 `preview` 和 `full`。若接口要求 `formal`，A 需做映射。
- 建议统一为 `preview | formal`，A 模块适配。

---

## 五、后续行动

### A 模块侧（改造计划）

| 优先级 | 改造项 | 影响范围 | 预计工时 |
|--------|-------|---------|---------|
| P0 | 统一响应格式解包：在 `_request` 中提取 `data` 字段，基于 `code` 判错 | `api_client.py` 全部方法 | 0.5h |
| P0 | `save_page_snapshot` 新增 `task_type`、`user_prompt`、`task_id`，`html` → `raw_html` | `api_client.py` + `handlers.py` 调用点 | 0.5h |
| P0 | `start_crawl_task` 新增 `task_type`、`user_prompt`、`ai_model`、`ai_api_url` | `api_client.py` + `crawler.py` 调用点 | 0.5h |
| P1 | `update_seed_status` 迁移到 `seed_id`（或维持 `url` 兼容） | `api_client.py` + `crawler.py` Worker 流程 | 1h |
| P2 | 新增 `generate_rules_api` 方法对接 `POST /api/ai/generate-rules/` | `api_client.py` | 0.5h |
| P3 | 启动时健康检查 `GET /api/health/` | `api_client.py` 或 Worker 启动逻辑 | 0.2h |
| P3 | `task_type` 取值 `full` → `formal` 映射 | `crawler.py` + `run_crawler.py` | 0.2h |

### 需要 C 侧确认的事项

1. **统一响应格式**：确认 `{code, msg, data}` 是否已部署到所有接口，错误响应格式是否一致。
2. **`seed_id` vs `url`**：`/api/seeds/status/` 是否支持 `url` 兼容参数，还是强制 `seed_id`。
3. **字段保留**：`/api/pagesnapshot/` 的 `category` 和 `images` 字段、`/api/crawl/start/` 的 `seed_url` 和 `max_depth` 字段是否仍保留。
4. **认证要求**：A 模块调用的接口是否需要 Token 认证。
5. **字段补充**：`/api/tasks/{id}/result/` 的入参是否包含 `failed_pages`、`report`、`error_message`。
