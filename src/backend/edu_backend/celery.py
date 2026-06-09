"""
文件名: celery.py
作用: Celery 异步任务队列初始化配置
主要功能:
    1. 初始化 Celery 应用实例
    2. 自动发现已注册 Django 应用中的 tasks.py 模块
    3. 供 Worker 和 Beat 调度器启动使用
"""

import os
from celery import Celery

# 设置 Django 配置文件为默认
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_backend.settings')

# 创建 Celery 应用实例
app = Celery('edu_backend')

# 从 Django settings 加载配置（CELERY_ 前缀的配置项）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有已注册 Django 应用中的 tasks.py
app.autodiscover_tasks()
