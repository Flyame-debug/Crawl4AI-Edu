import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_backend.settings')
django.setup()

from apps.api.models import CrawlTask, PageSnapshot

# 查看最新任务
task = CrawlTask.objects.order_by('-created_at').first()
if task:
    print(f"=== 最新任务 ===")
    print(f"任务ID: {task.task_id}")
    print(f"状态: {task.status}")
    print(f"错误: {task.error_message}")
    print(f"成功页数: {task.success_pages}")
    print(f"总页数: {task.total_pages}")
    print(f"创建时间: {task.created_at}")
    
    # 查看任务期间的新增页面
    new_pages = PageSnapshot.objects.filter(created_at__gte=task.created_at)
    print(f"\n任务期间新增页面数: {new_pages.count()}")
    for page in new_pages[:3]:
        print(f"  - {page.url}")
else:
    print("没有找到任务")