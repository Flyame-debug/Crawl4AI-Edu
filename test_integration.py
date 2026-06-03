# test_integration.py
import sys
import os
from pathlib import Path

# 设置路径
PROJECT_ROOT = Path(__file__).parent  # E:\Crawl4AI
DJANGO_ROOT = PROJECT_ROOT / "src" / "backend"  # E:\Crawl4AI\src\backend

# 添加所有需要的路径
sys.path.insert(0, str(PROJECT_ROOT))      # 为了导入 sandbox
sys.path.insert(0, str(DJANGO_ROOT))       # 为了导入 Django 模块

print("=" * 60)
print("Crawl4AI 集成测试")
print(f"项目根目录: {PROJECT_ROOT}")
print(f"Django根目录: {DJANGO_ROOT}")
print("=" * 60)

# 测试0: 检查关键目录
print("\n[0/7] 检查目录结构...")
checks = [
    ("sandbox", PROJECT_ROOT / "sandbox"),
    ("apps", DJANGO_ROOT / "apps"),
    ("edu_backend", DJANGO_ROOT / "edu_backend"),
    ("utils", DJANGO_ROOT / "utils"),
]
for name, path in checks:
    if path.exists():
        print(f"  ✓ {name}: {path}")
    else:
        print(f"  ✗ {name}: {path} 不存在")

# 测试1: Django 设置
print("\n[1/7] 测试 Django 设置...")
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_backend.settings')
    import django
    django.setup()
    print("✓ Django 初始化成功")
except Exception as e:
    print(f"✗ Django 初始化失败: {e}")

# 测试2: Django 模型
print("\n[2/7] 测试 Django 模型...")
try:
    from apps.api.models import PageSnapshot, SeedURL, CrawlerConfig
    print("✓ PageSnapshot, SeedURL, CrawlerConfig 导入成功")
except Exception as e:
    print(f"✗ Django 模型导入失败: {e}")

# 测试3: sandbox standalone_crawler
print("\n[3/7] 测试 sandbox.standalone_crawler...")
try:
    from sandbox.standalone_crawler import crawl
    print("✓ crawl 函数导入成功")
except Exception as e:
    print(f"✗ standalone_crawler 导入失败: {e}")

# 测试4: sandbox fetcher
print("\n[4/7] 测试 sandbox.fetcher...")
try:
    from sandbox.fetcher import async_fetch, FetchError
    print("✓ async_fetch 导入成功")
except Exception as e:
    print(f"✗ fetcher 导入失败: {e}")

# 测试5: sandbox link
print("\n[5/7] 测试 sandbox.link...")
try:
    from sandbox.link import extract_links, create_bloom_filter
    print("✓ extract_links, create_bloom_filter 导入成功")
except Exception as e:
    print(f"✗ link 导入失败: {e}")
    # 如果是缺少 pybloom_live
    if "pybloom_live" in str(e):
        print("  提示: 请运行 pip install pybloom-live")

# 测试6: utils 工具
print("\n[6/7] 测试 utils 工具...")
try:
    from utils.minio_client import MinioClient
    print("✓ MinioClient 导入成功")
except Exception as e:
    print(f"✗ MinioClient 导入失败: {e}")

try:
    from utils.robot_checker import robot_checker
    print("✓ robot_checker 导入成功")
except Exception as e:
    print(f"✗ robot_checker 导入失败: {e}")

# 测试7: API 视图函数
print("\n[7/7] 测试 apps.api.views 中的新增函数...")
try:
    from apps.api.views import start_crawl, get_crawl_status
    print("✓ start_crawl 和 get_crawl_status 函数已定义")
except ImportError as e:
    print(f"✗ 新增函数未找到: {e}")
except Exception as e:
    print(f"✗ 导入失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)