# test_api.py
import requests
import json

# 测试启动爬虫
url = "http://127.0.0.1:8000/api/crawl/start/"
data = {
    "seed_url": "https://httpbin.org/html",
    "max_depth": 1
}

print("=" * 50)
print("测试爬虫启动 API")
print("=" * 50)

try:
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")