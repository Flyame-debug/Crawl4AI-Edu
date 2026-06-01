"""
功能：统计 API 路由配置
用途：把 /api/stats/ 映射到统计视图
调用方：被 edu_backend/urls.py 包含
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_stats, name='stats'),
]