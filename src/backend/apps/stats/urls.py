"""
功能：统计模块路由配置
用途：将统计API的URL路径映射到视图函数
- /api/stats/ -> get_stats 视图
调用方：被总路由 edu_backend/urls.py 包含
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_stats, name='stats'),
]