# 成员AC对接 接口文档与问题解答


## 一、接口基础信息

| 项目 | 值 |
|------|-----|
| 后端地址 | `http://127.0.0.1:8000` |
| 数据格式 | 请求/响应均为 `application/json` |
| 字符编码 | UTF-8 |

---

## 二、接口清单

| 序号 | 方法 | 地址 | 用途 | 谁用 |
|------|------|------|------|------|
| 1 | GET | `/api/crawler/config/db/` | 获取爬虫配置 | A |
| 2 | GET | `/api/seeds/pending/` | 获取待爬种子 | A |
| 3 | POST | `/api/seeds/status/` | 更新种子状态 | A |
| 4 | POST | `/api/images/upload/` | 上传图片到MinIO | A |
| 5 | POST | `/api/pagesnapshot/` | 保存抓取的页面 | A |
| 6 | POST | `/api/crawl/start/` | 启动爬虫任务 | A/D |
| 7 | POST | `/api/tasks/{task_id}/result/` | 上报任务结果 | A |
| 8 | GET | `/api/tasks/{task_id}/` | 查询任务状态 | A/D |

---

## 三、接口详细说明

### 接口1：获取爬虫配置

**请求**

```
GET /api/crawler/config/db/
```

**响应**

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

| 字段 | 类型 | 说明 |
|------|------|------|
| `concurrency` | int | 最大并发数 |
| `request_delay` | float | 请求间隔（秒） |
| `max_depth` | int | 最大爬取深度 |
| `allowed_domains` | array | 允许的域名白名单 |
| `white_list_patterns` | array | URL路径白名单正则 |
| `enable_dead_check` | bool | 是否启用死链检测 |

---

### 接口2：获取待爬种子

**请求**

```
GET /api/seeds/pending/?limit=10
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | int | 否 | 每次返回数量，默认10 |

**响应**

```json
{
  "count": 3,
  "seeds": [
    {
      "id": 1,
      "url": "https://httpbin.org/html",
      "school": "清华大学",
      "category": "师资",
      "need_render": false
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `count` | int | 本次返回数量 |
| `seeds[].id` | int | 种子ID（数据库自增） |
| `seeds[].url` | string | 目标URL |
| `seeds[].school` | string | 所属高校 |
| `seeds[].category` | string | 分类（师资/课程/科研） |
| `seeds[].need_render` | bool | 是否需要动态渲染 |

---

### 接口3：更新种子状态

**请求**

```
POST /api/seeds/status/
```

**请求体**

```json
{
  "url": "https://httpbin.org/html",
  "status": "success"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | ✅ | 种子URL |
| `status` | string | ✅ | 状态值（见下表） |

**支持的状态值**

| 状态 | 含义 | 使用时机 |
|------|------|----------|
| `pending` | 待爬取 | 初始状态 |
| `crawling` | 爬取中 | 开始爬取时 |
| `success` | 成功 | 爬取完成后 |
| `failed` | 失败 | 爬取出错时 |
| `blocked` | 被禁止 | robots.txt禁止 |

**响应（成功-200）**

```json
{
  "status": "ok",
  "url": "https://httpbin.org/html",
  "new_status": "success"
}
```

**响应（失败-404）**

```json
{
  "error": "seed not found"
}
```

**响应（失败-400）**

```json
{
  "error": "invalid status"
}
```

---

### 接口4：上传图片

**请求**

```
POST /api/images/upload/
```

**方式1：base64（推荐）**

```json
{
  "image_base64": "iVBORw0KGgoAAAANS...",
  "filename": "teacher_photo.jpg"
}
```

**方式2：multipart/form-data**

```
files={"image": (filename, file_handle)}
```

**响应（成功-200）**

```json
{
  "success": true,
  "url": "http://127.0.0.1:9000/crawl4ai/images/2cd8bde463f5d82aae0f0cec061d6b8f.jpg",
  "image_id": "2cd8bde463f5d82aae0f0cec061d6b8f",
  "filename": "images/2cd8bde463f5d82aae0f0cec061d6b8f.jpg"
}
```

| 字段 | 说明 |
|------|------|
| `success` | 是否成功 |
| `url` | 图片访问地址（可直接用） |
| `image_id` | 图片唯一标识 |
| `filename` | 存储的文件名 |

**响应（失败-400）**

```json
{
  "error": "请提供 image 文件或 image_base64"
}
```

---

### 接口5：保存页面数据

**请求**

```
POST /api/pagesnapshot/
```

**请求体**

```json
{
  "url": "https://httpbin.org/html",
  "markdown": "<html>...完整的HTML内容...</html>",
  "category": "师资",
  "images": [
    {
      "original_url": "https://httpbin.org/image1.jpg",
      "stored_url": "http://127.0.0.1:9000/crawl4ai/images/abc123.jpg"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | ✅ | 页面URL |
| `markdown` | string | ✅ | 页面内容（目前可存HTML） |
| `category` | string | ❌ | 分类，不传则自动识别 |
| `images` | array | ❌ | 图片列表 |

**响应（成功）**

```json
{
  "action": "created",
  "data": {
    "id": 123,
    "url": "https://httpbin.org/html",
    "category": "师资",
    "created_at": "2026-06-04T10:00:00Z"
  }
}
```

| `action`值 | 含义 |
|------------|------|
| `created` | 新创建 |
| `updated` | 更新版本 |
| `skipped` | 内容无变化，跳过 |

**响应（失败-400）**

```json
{
  "error": "url 和 markdown 为必填字段"
}
```

---

### 接口6：启动爬虫任务

**请求**

```
POST /api/crawl/start/
```

**请求体**

```json
{
  "seed_url": "https://httpbin.org/html",
  "max_depth": 2,
  "config": {
    "max_concurrent": 5,
    "request_delay": 1.0
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `seed_url` | string | ✅ | 种子URL |
| `max_depth` | int | ❌ | 最大深度，默认2 |
| `config` | object | ❌ | 额外配置 |

**响应（成功-200）**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Crawl task started successfully.",
  "status_url": "/api/crawl/status/550e8400-e29b-41d4-a716-446655440000/",
  "created_at": "2026-06-04T10:00:00Z"
}
```

**⚠️ 重要**：返回的 `task_id` 需要在后续上报结果时使用。

---

### 接口7：上报任务结果

**请求**

```
POST /api/tasks/{task_id}/result/
```

**URL参数**

| 参数 | 说明 |
|------|------|
| `{task_id}` | 从启动接口获取的任务ID |

**请求体**

```json
{
  "status": "completed",
  "total_pages": 50,
  "success_pages": 48,
  "failed_pages": 2,
  "report": "抓取完成，成功率96%"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | ✅ | `completed` 或 `failed` |
| `total_pages` | int | ❌ | 总页面数 |
| `success_pages` | int | ❌ | 成功数 |
| `failed_pages` | int | ❌ | 失败数 |
| `report` | string | ❌ | 统计报告文本 |
| `error_message` | string | ❌ | 失败时的错误信息 |

**响应（成功-200）**

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed"
}
```

**响应（失败-404）**

```json
{
  "error": "Task not found"
}
```

---

### 接口8：查询任务状态

**请求**

```
GET /api/tasks/{task_id}/
```

**响应**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "seed_url": "https://httpbin.org/html",
  "max_depth": 2,
  "total_pages": 50,
  "success_pages": 48,
  "failed_pages": 2,
  "error_message": null,
  "report": "抓取完成，成功率96%",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T10:30:00Z"
}
```

---

## 四、问题解答

### Q1：`/api/seeds/status/` 接受 url 还是 seed_id？

**答：接受 `url`（字符串），不是 seed_id。**

示例：

```json
{"url": "https://httpbin.org/html", "status": "success"}
```

---

### Q2：种子对象中是否包含 task_id？如何获取任务 ID？

**答：种子对象不包含 `task_id`。**

获取方式：

1. 调用 `POST /api/crawl/start/` 启动任务
2. 从响应中获取 `task_id`
3. 用这个 `task_id` 上报结果

```python
# 启动任务
resp = requests.post("/api/crawl/start/", json={"seed_url": url})
task_id = resp.json()["task_id"]

# 上报结果
requests.post(f"/api/tasks/{task_id}/result/", json={...})
```

---

### Q3：`/api/pagesnapshot/` 的 images 字段格式？

**答：有 `images` 字段，是 JSON 数组。**

每个图片对象格式：

```json
{
  "original_url": "原始图片URL",
  "stored_url": "上传后的MinIO地址"
}
```

---

### Q4：`/api/images/upload/` 的请求方式和返回格式？

**答：支持两种方式，推荐 base64。**

| 方式 | Content-Type | 请求体 |
|------|--------------|--------|
| base64 | `application/json` | `{"image_base64": "..."}` |
| form-data | `multipart/form-data` | `files={"image": file}` |

返回格式：

```json
{
  "success": true,
  "url": "http://127.0.0.1:9000/crawl4ai/images/xxx.jpg",
  "image_id": "2cd8bde463f5d82aae0f0cec061d6b8f"
}
```

---

## 五、完整的爬虫工作流程

```
1. 启动时调用接口1 → 获取配置
   ↓
2. 调用接口2 → 获取待爬种子
   ↓
3. 调用接口3 → 更新种子状态为 "crawling"
   ↓
4. 调用接口6 → 启动任务，获取 task_id
   ↓
5. 开始爬取
   ├── 每张图片 → 调用接口4 → 获得图片URL
   └── 每个页面 → 调用接口5 → 保存页面数据
   ↓
6. 爬取完成 → 调用接口7 → 上报结果
   ↓
7. 调用接口3 → 更新种子状态为 "success"
```

---

## 六、测试命令（供验证）

```bash
# 1. 测试配置接口
curl http://127.0.0.1:8000/api/crawler/config/db/

# 2. 测试种子接口
curl "http://127.0.0.1:8000/api/seeds/pending/?limit=5"

# 3. 测试启动任务
curl -X POST http://127.0.0.1:8000/api/crawl/start/ \
  -H "Content-Type: application/json" \
  -d '{"seed_url": "https://httpbin.org/html"}'

# 4. 测试图片上传
curl -X POST http://127.0.0.1:8000/api/images/upload/ \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "iVBORw0KGgoAAAANS..."}'
```
