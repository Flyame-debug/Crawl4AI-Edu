# A 模块与后端接口对接反馈（基于第二版接口文档）

> **文档版本**：基于成员 C 的 `第二版接口文档（面向A,B,D）.md` V2.0
> **审查范围**：`sandbox/standalone_crawler/api_client.py`（8 个方法）、`crawler.py`（Worker/API/Local 三条路径）、`handlers.py`（单页处理）
> **更新日期**：2026-06-15
> **当前状态**：C 已确认全部问题，A 模块 P0 适配已完成（响应解包、pagesnapshot 新字段、crawl/start 新字段、health check、full→formal 映射）

---

## 一、C 回复确认汇总

| # | 问题 | C 回复 | A 适配状态 |
|---|------|--------|-----------|
| 1 | 统一响应格式 | `{code, msg, data}`，错误 `data: null`，分页 `{count, results}` | ✅ 已完成：`_request` 解包 `data`，`code != 200` 抛 `APIClientError` |
| 2 | seeds/status 入参 | 同时支持 `url` 和 `seed_id`，继续用 `url` | ✅ 无需修改 |
| 3 | pagesnapshot 字段 | `category`/`images` 保留；`html` → `raw_html`；新增 `task_type`/`user_prompt`/`task_id`（必填） | ✅ 已完成：`api_client.py` + `handlers.py` 均已更新 |
| 4 | crawl/start 字段 | 原有字段全部保留，新增 `task_type`/`user_prompt`/`ai_model`/`ai_api_url` | ✅ 已完成：`api_client.py` + `crawler.py` 调用点均已更新 |
| 5 | tasks/{id}/result/ | `failed_pages`/`report`/`error_message` 都接受 | ✅ 无需修改 |
| 6 | 认证机制 | 联调阶段暂不需要 Token，生产环境启用 JWT 时提前通知 | ✅ 无需修改 |
| 7 | task_type 取值 | 统一 `preview \| formal`，A 做 `full → formal` 映射 | ✅ 已完成：`_run_bfs_crawl` 内部映射 |
| 8 | AI generate-rules | 建议保持本地直连，P2 再迁移 | ✅ 无需修改 |
| 9 | health check | 建议增加启动时健康检查 | ✅ 已完成：`APIClient.check_health()` + Worker 启动调用 |

---

## 二、已完成的代码适配

### 2.1 api_client.py（第 8 个方法 + 响应解包 + 字段变更）

| 变更项 | 说明 |
|--------|------|
| `_request` 响应解包 | 解析 `{code, msg, data}` 信封；`code==200` 返回 `data`；`code!=200` 且非 5xx 抛出 `APIClientError`；5xx 继续重试 |
| `get_pending_seeds` | 分页格式 `{count, results}` → 内部映射为 `{count, seeds}`，保持调用方兼容 |
| `save_page_snapshot` | 签名新增 `task_id`、`task_type`、`user_prompt`（keyword-only）；`html` 参数改为 `raw_html`；保留 `category`、`images` |
| `start_crawl_task` | 签名新增 `task_type`、`user_prompt`、`ai_model`、`ai_api_url`（keyword-only）；保留 `seed_url`、`max_depth`、`config` |
| `check_health` | 新增方法 `GET /api/health/` → `bool`，Worker 启动时调用 |

### 2.2 handlers.py

- `process_page` 签名新增 `task_type`、`user_prompt` 可选参数
- `save_page_snapshot` 调用点：新增 `task_id`、`task_type`、`user_prompt`；`html` → `raw_html`

### 2.3 crawler.py

- `crawl()` / `_run_bfs_crawl()` 签名新增 `user_prompt` 参数
- `_run_bfs_crawl` 内部：`task_type=="full"` 映射为 `_api_task_type="formal"`
- 三处 `_run_bfs_crawl` 调用点（Worker/API/Local）均传递 `user_prompt`
- 两处 `start_crawl_task` 调用点均传递 `task_type="formal"` + `user_prompt`
- `_worker` → `process_page` 传递 `task_type=_api_task_type` + `user_prompt`
- Worker 启动时调用 `api_client.check_health()`

---

## 三、P2 预留事项

| 事项 | 说明 | 优先级 |
|------|------|--------|
| `POST /api/ai/generate-rules/` | 当前 A 本地直连 Ollama，P2 可迁移到后端中转 | 低 |
| Token 认证 | 生产环境启用 JWT 后，在 `_request` 中添加 `Authorization` 头 | 中 |
| `GET /api/crawler/status/` | 当前未实现，前端展示用，非 A 模块核心依赖 | 低 |

---

## 四、验证结果

- `api_client.py` smoke test：8 个方法全部通过，响应解包逻辑正确
- `handlers.py` smoke test：通过，`save_page_snapshot` 新字段传递正常
- 导入检查：`crawl()`、`_run_bfs_crawl()`、`process_page()` 签名均含 `user_prompt`/`task_type`
- `APIClient.check_health` 方法存在且可调用
