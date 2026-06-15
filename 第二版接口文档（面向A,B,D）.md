# Crawl4AI 教育知识库采集系统
## 后端接口文档（成员C 输出 | 分角色对接版）
**版本**：V2.0（适配双AI、预览采集、模板分类、历史模板）
**技术栈**：Django 5.2 + DRF | PostgreSQL | Redis+Celery | MinIO
**迭代划分**：P1（基础新功能）、P2（AI能力）
**说明**：原有27个接口全部保留，仅增补字段/逻辑；新增3个接口，按对接角色拆分，方便A/B/D联调。

---

# 通用约定
1. 请求格式：`application/json`
2. 统一返回格式
```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```
3. 任务类型枚举
- `preview`：预览任务（最多10条，临时存储，不长期归档）
- `formal`：正式采集任务（全量抓取，入库归档）
4. 页面处理状态枚举（`process_status`）
- `pending`：待处理
- `raw_converted`：已基础转Markdown
- `ai_cleaned`：已AI清洗+结构化提取
- `error`：处理失败

---

# 一、公共接口（全员可用：A/B/D）
## 1. 用户认证接口
### 1.1 用户登录
- 地址：`POST /api/auth/login/`
- 入参：
```json
{
  "username": "string",
  "password": "string"
}
```
- 出参：用户信息 + Token
- 对接方：D（前端）

### 1.2 用户注册
- 地址：`POST /api/auth/register/`
- 入参：`username、password、email`
- 对接方：D（前端）

## 2. 系统监控&健康检查
### 2.1 全局统计数据（仪表盘）
- 地址：`GET /api/stats/`
- 出参：任务总数、成功数、模板数量等统计
- 对接方：D

### 2.2 爬虫状态
- 地址：`GET /api/crawler/status/`
- 对接方：A/D

### 2.3 日志查询
- 地址：`GET /api/logs/`
- 对接方：全员

### 2.4 服务健康检查
- 地址：`GET /api/health/`
- 对接方：全员

---

# 二、对接 成员A（爬虫 + 采集脚本AI）专用接口
> 用途：爬虫抓取、任务调度、AI生成采集规则、图片上传、页面快照上报

## 1. 爬虫配置获取
### 1.1 获取全局爬虫配置
- 地址：`GET /api/crawler/config/db/`
- 出参：爬虫并发、域名白名单、超时、渲染配置
- 新增透传字段：无，原有逻辑不变

## 2. 种子URL管理
### 2.1 获取待爬种子
- 地址：`GET /api/seeds/pending/`
- 出参：种子列表、`url、school、category、need_render`

### 2.2 更新种子状态
- 地址：`POST /api/seeds/status/`
- 入参：`seed_id、status`

## 3. 图片上传（MinIO）
### 3.1 图片上传
- 地址：`POST /api/images/upload/`
- 入参：图片文件（multipart/form-data / base64）
- 出参：`success、url、image_id、filename`

## 4. 页面快照上报（核心）
### 4.1 保存网页快照
- 地址：`POST /api/pagesnapshot/`
- **新增入参**：`task_type、user_prompt`
- 入参：
```json
{
  "url": "string",
  "raw_html": "string",
  "markdown": "string",
  "task_id": "string",
  "task_type": "preview | formal",
  "user_prompt": "用户提取指令"
}
```
- 内部逻辑：自动标记 `process_status = raw_converted`，通知B进入清洗流程

## 5. 爬虫任务启停&结果上报
### 5.1 启动爬虫任务
- 地址：`POST /api/crawl/start/`
- **新增入参**：`task_type、user_prompt、ai_model、ai_api_url`

### 5.2 上报任务执行结果
- 地址：`POST /api/tasks/{id}/result/`
- 入参：`task_id、status、total_pages、success_pages`

## 6. P2新增：AI生成采集规则（A专属）
### 6.1 生成 XPath/CSS 采集脚本
- 地址：`POST /api/ai/generate-rules/`
- 用途：根据用户指令+页面DOM骨架，生成抓取规则
- 入参：
```json
{
  "ai_model": "qwen2:7b",
  "ai_api_url": "http://127.0.0.1:11434",
  "user_prompt": "提取教师姓名、职称",
  "html_skeleton": "精简DOM结构文本"
}
```
- 出参：
```json
{
  "code": 200,
  "data": {
    "rule_content": "//div[@class='name']",
    "status": "success",
    "error_msg": ""
  }
}
```
- 逻辑：后端中转，由A调用本地AI，结果回填至任务/模板字段

---

# 三、对接 成员B（数据清洗 + 清洗提取AI）专用接口
> 用途：获取待清洗页面、上报AI清洗结果、更新结构化数据与状态

## 1. 无单独专属查询接口，依托**页面快照表 + 状态接口**交互
### 1.1 上报AI清洗结果 & 更新页面状态（P2新增）
- 地址：`POST /api/ai/clean-status/`
- 用途：B完成AI清洗+规则校验后，上报结果、修改状态
- 入参：
```json
{
  "snapshot_id": "int",
  "process_status": "ai_cleaned | error",
  "extracted_data": {
    "name": "姓名",
    "title": "职称",
    "email": "邮箱",
    "research": "研究方向"
  },
  "error_info": "异常信息（可选）"
}
```
- 逻辑：
  1. 更新 `PageSnapshot.process_status`
  2. 保存结构化提取数据 `extracted_data`
  3. 数据同步至前端预览/正式库

## 2. 数据获取方式
B 直接读取数据库 `PageSnapshot` 表，筛选 `process_status = raw_converted` 数据进行清洗；
无需额外查询接口，后端开放表读写权限/内部服务调用。

---

# 四、对接 成员D（前端）专用接口
> 包含：模板管理、任务管理、历史模板、预览、下载、AI配置全量接口

## 1. 模板管理（全量改造，新增分类/AI配置/用户指令）
### 1.1 获取模板列表（支持分类筛选）
- 地址：`GET /api/templates/`
- **新增查询参数**：`category`
- 出参：模板基础信息 + 新增字段
  `category、ai_model、ai_api_url、ai_api_key、user_prompt、usage_count`

### 1.2 新建模板
- 地址：`POST /api/templates/`
- **新增入参**：`category、ai_model、ai_api_url、ai_api_key、user_prompt`

### 1.3 获取模板详情
- 地址：`GET /api/templates/{id}/`
- 出参：全量模板字段（含分类、AI配置、用户指令）

### 1.4 更新模板
- 地址：`PUT /api/templates/{id}/`
- 入参：同新建模板，包含所有新增字段

### 1.5 删除模板
- 地址：`DELETE /api/templates/{id}/`
- 逻辑不变

### 1.6 P1新增：个人中心-历史模板
- 地址：`GET /api/templates/history/`
- 查询参数：`page、size`（分页）
- 出参：用户历史使用模板、使用时间、使用次数

## 2. 任务控制接口（区分预览/正式任务）
### 2.1 启动采集任务（核心改造）
- 地址：`POST /api/tasks/start/`
- **新增入参**：
```json
{
  "template_id": "int",
  "task_type": "preview | formal",
  "user_prompt": "前端输入的提取指令",
  "ai_model": "模型名",
  "ai_api_url": "AI地址",
  "ai_api_key": "密钥（可选）"
}
```
- 逻辑：
  - `preview`：限制10条数据，预览专用
  - `formal`：全量采集，入库归档
  - P2自动调用AI生成规则，回填前端高级代码框

### 2.2 暂停任务
- 地址：`POST /api/tasks/{id}/pause/`

### 2.3 停止任务
- 地址：`POST /api/tasks/{id}/stop/`

### 2.4 删除任务
- 地址：`DELETE /api/tasks/{id}/delete/`

## 3. 任务查询 & 预览 & 下载
### 3.1 任务列表
- 地址：`GET /api/tasks/`
- 出参新增：`task_type、generated_rule`（AI生成的脚本）

### 3.2 任务详情
- 地址：`GET /api/tasks/{id}/`

### 3.3 任务进度轮询
- 地址：`GET /api/tasks/{id}/progress/`

### 3.4 采集数据预览
- 地址：`GET /api/tasks/{id}/preview/`
- 优先返回结构化清洗数据，适配前端「数据预览」标签页

### 3.5 结果下载
- 地址：`GET /api/tasks/{id}/download/`
- 限制：`preview` 预览任务禁止下载，仅正式任务可导出 JSON/CSV

---

# 五、接口总清单 & 分阶段上线表
## 1. 接口数量统计
- 原有保留接口：27 个
- P1 新增接口：`/api/templates/history/` （1个）
- P2 新增接口：`/api/ai/generate-rules/`、`/api/ai/clean-status/`（2个）
- **合计接口总数：30 个**

## 2. 分阶段上线安排
### P1 第一周（无AI，必做验收项）
1. 所有模板/任务接口增补 `category、task_type、user_prompt` 字段
2. 上线：`/api/templates/history/` 历史模板接口
3. 完成预览任务（preview）逻辑：限制10条、临时存储

### P2 第二周（AI能力上线）
1. 上线：`/api/ai/generate-rules/`（A 生成采集脚本）
2. 上线：`/api/ai/clean-status/`（B 上报清洗结果）
3. 全链路联调：AI脚本生成 → 爬虫抓取 → AI清洗 → 前端展示

---

# 六、数据表新增/变更说明（供全员参考）
1. **Template 表**：新增 `category、ai_model、ai_api_url、ai_api_key、user_prompt`
2. **CrawlTask 表**：新增 `task_type、generated_rule`
3. **PageSnapshot 表**：扩展 `process_status` 枚举值
4. **新增表 UserTemplateHistory**：存储用户历史模板（对应历史模板接口）

---

# 七、角色对接极简说明
1. **成员A**
   - 使用：爬虫配置、种子、图片上传、页面快照、任务结果上报、AI生成规则接口
   - 接收：任务类型、用户指令、AI连接配置
   - 输出：HTML/Markdown、抓取结果、AI采集脚本

2. **成员B**
   - 无主动查询接口，**读数据库待清洗数据**
   - 调用：`/api/ai/clean-status/` 上报清洗状态与结构化数据

3. **成员D**
   - 全部模板、任务、历史模板、预览、下载、认证接口
   - 负责前端表单字段与接口入参一一对应

4. **成员C**
   - 维护所有接口、数据库、队列、存储、异常捕获、日志。