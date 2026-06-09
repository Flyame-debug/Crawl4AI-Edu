"""
文件名: __init__.py
作用: Django 项目包初始化，确保 Celery 应用随 Django 启动时自动加载
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
