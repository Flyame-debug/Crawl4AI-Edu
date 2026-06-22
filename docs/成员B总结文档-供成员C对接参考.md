# 成员B总结文档 —— 供成员C进行前后端对接参考

> 生成日期：2026-06-22  
> 用途：帮助成员C快速理解成员B的所有工作内容、接口约定、数据格式，便于前后端联调。

---

## 一、成员B角色与模块总览

| 模块 | 名称 | 状态 |
|------|------|------|
| 模块2 | Ollama 本地大模型部署与运维 | ✅ 已完成 |
| 模块3 | AI 智能清洗与结构化提取（核心） | ✅ 已完成 |
| 模块4 | 规则兜底校验 | ✅ 已完成 |
| 模块5 | 后端集成与状态上报 | ✅ 已完成（流水线集成测试待补充） |

B 的工作在整个系统中处于"数据处理中枢"的位置，负责接收成员A通过 Crawl4AI 转换后的 Markdown，经过 AI 清洗 + 规则校验，产出结构化数据写入 `extracted_data`。

---

## 二、全链路数据流（B 的位置）

```
用户操作(D) → 后端调度(C)
  → A：爬虫抓取 + Crawl4AI 基础清洗（HTML→Markdown）
  → C：入库 PageSnapshot，标记 process_status='raw_converted'
  → 【B 的环节】
      1. Celery 定时任务拉取 raw_converted 页面
      2. 调用清洗流水线 run_cleaning_pipeline()
      3. 流水线内部：AI清洗(模块3) → 规则校验(模块4) → 降级兜底
      4. 结果通过 PageSnapshotService.update_clean_result() 写入库
  → C：标记 process_status='ai_cleaned'，数据入库
  → D：前端展示
```

---

## 三、B 写入的数据结构（extracted_data）

B 最终写入 `PageSnapshot.extracted_data` 的 JSON 结构如下：

```json
{
    "page_type": "teacher",
    "content": "## 张三 教授\n\n**院系**: 计算机学院\n\n**联系方式**\n- 邮箱: zhangsan@edu.cn\n- 电话: 010-12345678\n\n**研究方向**\n- 机器学习\n- 数据挖掘",
    "method": "ai_ollama",
    "confidence": "high",
    "_validation": {
        "passed": true,
        "fixes": [],
        "warnings": []
    }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `page_type` | string | 页面类型：`teacher` / `course` / `research` / `unknown` |
| `content` | string | **核心字段**：AI 根据用户 `user_prompt` 提取并排版后的 **Markdown 文本**。前端建议用 `marked` 库渲染展示 |
| `method` | string | 提取方法，见下方枚举 |
| `confidence` | string | 置信度：`"high"` / `"medium"` / `"low"` |
| `_validation` | object | 模块4写入的校验结果：`{passed, fixes[], warnings[]}` |

### method 枚举值

| 值 | 含义 |
|-----|------|
| `ai_ollama` | AI 成功提取，规则校验通过 |
| `ai_ollama_fixed` | AI 提取后经规则修正 |
| `rule_fallback` | AI 不可用，纯规则兜底提取 |
| `extraction_error` | 所有方式均失败 |

---

## 四、process_status 状态与 B 的职责

### 状态枚举

```
pending        → 待处理（A 尚未处理）
raw_converted  → 已基础转 Markdown（A 完成，B 的输入）
ai_cleaned     → 已 AI 清洗（B 完成后标记）
error          → 处理失败（B 失败时标记）
```

### B 操作的状态流转

```
raw_converted → [B 流水线] → AI 成功+规则校验通过 → ai_cleaned     (method=ai_ollama/ai_ollama_fixed)
                           → AI 失败+重试耗尽+降级成功 → ai_cleaned  (method=rule_fallback)
                           → AI 失败+重试耗尽+降级失败 → ai_cleaned  (method=extraction_error)
                           → markdown 为空/硬错误 → error
                           → AI 暂时失败(还有重试次数) → 保持 raw_converted（等待 Celery 重试）
```

### B 只读不写的字段

- `markdown` — 成员A 写入，B 读取但不修改
- `user_prompt` — 前端写入，B 读取但不修改
- `raw_html` — 成员A 写入，B 不读取
- `task_type` — C 管理，B 只读

### B 负责写入的字段

- `extracted_data` — JSONField（核心产出）
- `process_status` — 更新为 `ai_cleaned` 或 `error`
- `error_info` — 失败时写入，最多 500 字符
- `processed_at` — 处理完成时间

---

## 五、B 交付的关键文件清单

| 文件 | 类型 | 行数 | 作用 |
|------|------|------|------|
| `services/ai_cleaner.py` | 新建 | ~286行 | 模块3：AI 清洗核心，独立调用 Ollama /api/generate |
| `services/rule_validator.py` | 新建 | ~1079行 | 模块4：规则兜底校验（2个公开函数+18个内部函数） |
| `services/cleaning_pipeline.py` | 新建 | ~229行 | 模块5：流水线主函数，串联 AI→校验→降级 |
| `services/ai_service.py` | 修改 | — | 模块2：新增 `check_health()` 和 `list_models()` 方法 |
| `tasks.py` | 修改 | — | 新增 `process_ai_cleaning_task`（改造）和 `monitor_ollama_health` |
| `management/commands/check_ollama.py` | 新建 | — | 模块2：手动健康检查命令 |
| `settings.py` | 修改 | — | 新增 `monitor-ollama-health` Beat 配置 |
| `tests/test_ai_cleaning.py` | 新建 | — | AI 清洗单元测试（39条全通过） |
| `tests/test_rule_validator.py` | 新建 | — | 规则校验单元测试（101条全通过） |
| `tests/test_cleaning_pipeline.py` | 新建 | — | 📝 流水线集成测试（待编写） |

---

## 六、B 与 C 的代码接口约定

### 6.1 B 获取待处理数据

B 通过以下方式获取需要清洗的页面：

```python
# 方式一：ORM 直接查询（tasks.py 中使用）
PageSnapshot.objects.filter(
    process_status='raw_converted'
).exclude(
    Q(markdown__isnull=True) | Q(markdown='')
)[:batch_size]
```

对应的 HTTP 接口（如果走 API）：
```
GET /api/pagesnapshot/?process_status=raw_converted
```

### 6.2 B 上报清洗结果

B 通过 `PageSnapshotService.update_clean_result()` 写入数据库（**不走 HTTP，直接调用服务层**）：

```python
# 成功时
PageSnapshotService.update_clean_result(
    snapshot_id=page.id,
    extracted_data=extracted_data,
    process_status='ai_cleaned',
)

# 失败时
PageSnapshotService.update_clean_result(
    snapshot_id=page.id,
    extracted_data={},
    process_status='error',
    error_info=result['error'][:500],
)
```

对应的 HTTP 接口（备用，当前未使用）：
```
POST /api/ai/clean-status/
Body: { snapshot_id, process_status, extracted_data, error_info }
```

> **注意**：`views.py` 中的 `update_clean_status`（第870行）与 `snapshot_service.py` 的 `update_clean_result()` 逻辑重复。建议 C 后续统一入口，让视图层调用服务层方法。

### 6.3 内部流水线返回值约定

`run_cleaning_pipeline()` 返回统一结构，供 `tasks.py` 消费：

```python
# AI 成功/降级成功
{'action': 'completed', 'extracted_data': {...}, 'error': None}

# AI 暂时失败，需重试（不写数据库，由 tasks.py 触发 Celery 重试）
{'action': 'retry', 'extracted_data': None, 'error': 'Ollama API调用失败'}

# 硬错误（如 markdown 为空）
{'action': 'error', 'extracted_data': None, 'error': '输入Markdown内容为空'}
```

---

## 七、Celery 任务详情（B 负责的）

### 7.1 process_ai_cleaning_task（核心任务）

| 属性 | 值 |
|------|-----|
| 调度方式 | Celery Beat，每5分钟 |
| 批次大小 | 默认20条 |
| 最大重试 | 3次 |
| 退避策略 | 指数退避：60s → 120s → 240s |
| 处理对象 | `process_status='raw_converted'` 且 markdown 非空 |
| 成功写入 | `process_status='ai_cleaned'` |
| 降级逻辑 | 重试耗尽后自动降级到规则兜底 `extract_by_rules_fallback()` |

### 7.2 monitor_ollama_health（健康监控）

| 属性 | 值 |
|------|-----|
| 调度方式 | Celery Beat，每5分钟 |
| 最大重试 | 1次 |
| 行为 | 健康时静默（debug日志），异常时记录 error 日志 |
| 不写入数据库 | ✅ |

### 7.3 Beat 调度配置（settings.py 中需确保存在）

```python
CELERY_BEAT_SCHEDULE = {
    # B 的 AI 清洗任务
    'process-ai-cleaning': {
        'task': 'apps.api.tasks.process_ai_cleaning_task',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'default'},
    },
    # B 的 Ollama 健康监控
    'monitor-ollama-health': {
        'task': 'apps.api.tasks.monitor_ollama_health',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'default'},
    },
}
```

---

## 八、Ollama 依赖说明

| 项目 | 值 |
|------|-----|
| API 地址 | `http://127.0.0.1:11434` |
| 默认模型 | `qwen2:7b` |
| 请求超时 | 120秒 |
| 截断长度 | 前 12000 字符 |
| 温度参数 | `temperature=0.3`, `top_p=0.9` |
| API 端点 | `POST /api/generate`（直接 HTTP 调用，不复用 ai_service.py） |
| 离线部署 | 纯本地推理，无 API Key 依赖 |

### 健康检查命令

```bash
# 手动检查
python manage.py check_ollama
python manage.py check_ollama --model qwen2:14b
```

---

## 九、错误处理与容错机制

### 分层容错

```
第1层：AI 调用失败 → 返回 retry，Celery 60s 后重试
第2层：AI 第2次失败 → 返回 retry，Celery 120s 后重试
第3层：AI 第3次失败 → 重试耗尽，降级到规则兜底 extract_by_rules_fallback()
第4层：规则兜底也失败 → method='extraction_error'，写入 ai_cleaned
第5层：markdown 为空 → 直接标记 error
```

### 重试信号机制

- B 定义了 `RetryNeededException` 自定义异常
- 流水线返回 `action='retry'` → tasks.py 捕获后抛出异常 → Celery 指数退避重试
- 重试期间页面保持 `raw_converted` 状态，不影响其他任务

### 并发安全

- `tasks.py` 中有状态前置检查：`if page.process_status == 'ai_cleaned': continue`
- `PageSnapshotService.update_clean_result()` 使用行级锁

---

## 十、C 需要关注的前后端对接要点

### 10.1 前端展示 extracted_data.content

`extracted_data.content` 是 **Markdown 文本**，前端需要使用 Markdown 渲染器展示。建议使用 `marked` 库：

```javascript
import { marked } from 'marked';
const html = marked(extractedData.content);
```

### 10.2 process_status 筛选

前端数据列表/筛选功能需支持以下状态值：
- `raw_converted` — 等待 AI 清洗
- `ai_cleaned` — 清洗完成，可展示
- `error` — 处理失败

### 10.3 method 字段用于区分数据来源

前端或管理后台可展示来源标识：
- `ai_ollama` / `ai_ollama_fixed` — 🤖 AI 提取
- `rule_fallback` — 📋 规则兜底
- `extraction_error` — ⚠️ 提取失败

### 10.4 confidence 用于置信度标识

- `high` — 绿色/正常
- `medium` — 黄色/待确认
- `low` — 红色/需人工审核

### 10.5 统计/仪表盘数据

C 的统计 API 如需区分清洗状态，可使用以下条件：
```python
# AI 成功
PageSnapshot.objects.filter(process_status='ai_cleaned', extracted_data__method='ai_ollama')

# 规则兜底
PageSnapshot.objects.filter(process_status='ai_cleaned', extracted_data__method='rule_fallback')

# 处理失败
PageSnapshot.objects.filter(process_status='error')
```

### 10.6 待办事项

| 事项 | 优先级 | 说明 |
|------|--------|------|
| 流水线集成测试 | 中 | `tests/test_cleaning_pipeline.py` 待编写，前后端对接后可补充 |
| 统一 update_clean_result 入口 | 低 | views.py 和 snapshot_service.py 中有重复逻辑，建议后续统一 |
| 前端 Markdown 渲染 | 高 | 前端需确保 `marked` 库正确渲染 `content` 字段 |
| Ollama 服务保障 | 高 | 确保生产环境 Ollama 常驻运行，否则所有页面走降级规则 |

---

## 十一、B 未修改的文件（C 可放心维护）

| 文件 | 说明 |
|------|------|
| `services/conversion.py` | A 的 HTML→MD 转换 |
| `services/extraction/` | 旧模块6代码 |
| `management/commands/process_conversion.py` | A 的批量转换命令 |
| `models.py` | 数据库模型（C 维护） |
| `views.py` | API 视图（C 维护） |
| `urls.py` | 路由（C 维护） |

---

## 十二、常用调试命令（C 可能需要）

```bash
# 查看各状态页面数量
python manage.py shell -c "
from apps.api.models import PageSnapshot
print('raw_converted:', PageSnapshot.objects.filter(process_status='raw_converted').count())
print('ai_cleaned:', PageSnapshot.objects.filter(process_status='ai_cleaned').count())
print('error:', PageSnapshot.objects.filter(process_status='error').count())
"

# 查看某页面的提取结果
python manage.py shell -c "
from apps.api.models import PageSnapshot
p = PageSnapshot.objects.get(id=1)
print(p.extracted_data)
"

# 手动触发一次 AI 清洗（同步，调试用）
python manage.py shell -c "
from apps.api.tasks import process_ai_cleaning_task
print(process_ai_cleaning_task(batch_size=5))
"

# 重置某页面状态以便重新清洗
python manage.py shell -c "
from apps.api.models import PageSnapshot
p = PageSnapshot.objects.get(id=1)
p.process_status = 'raw_converted'
p.error_info = ''
p.save()
print('已重置')
"

# Ollama 健康检查
python manage.py check_ollama
```
