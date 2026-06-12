"""
功能：统计模块路由配置
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_stats, name='stats'),
    path('task/<str:task_id>/', views.get_task_detail, name='task_detail'),
]