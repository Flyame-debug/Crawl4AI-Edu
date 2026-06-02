"""
功能：API 路由配置
用途：把 URL 地址映射到对应的视图函数
- /api/pagesnapshot/ -> PageSnapshotViewSet
- /api/seedurl/ -> SeedURLViewSet
- /api/crawler/status/ -> 爬虫状态
- /api/logs/ -> 日志查询
- /api/crawler/config/ -> 爬虫配置
调用方：被 edu_backend/urls.py 包含
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 注册 ModelViewSet 路由
router = DefaultRouter()
router.register(r'pagesnapshot', views.PageSnapshotViewSet, basename='pagesnapshot')
router.register(r'seedurl', views.SeedURLViewSet, basename='seedurl')

urlpatterns = [
    # 自动生成的 CRUD 路由
    path('', include(router.urls)),
    
    # ========== 爬虫状态 API ==========
    path('crawler/status/', views.get_crawler_status, name='crawler_status'),
    
    # ========== 日志管理 API ==========
    path('logs/', views.get_logs, name='logs'),
    path('logs/files/', views.get_log_files, name='log_files'),
    
    # ========== 爬虫配置 API ==========
    path('crawler/config/', views.get_crawler_config, name='crawler_config'),
    path('crawler/config/update/', views.update_crawler_config, name='update_crawler_config'),
]