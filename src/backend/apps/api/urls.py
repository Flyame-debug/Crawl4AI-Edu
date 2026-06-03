"""
功能：API 路由配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pagesnapshot', views.PageSnapshotViewSet, basename='pagesnapshot')
router.register(r'seedurl', views.SeedURLViewSet, basename='seedurl')

urlpatterns = [
    path('', include(router.urls)),
    
    # ========== 原有 API ==========
    path('crawler/status/', views.get_crawler_status, name='crawler_status'),
    path('logs/', views.get_logs, name='logs'),
    path('logs/files/', views.get_log_files, name='log_files'),
    path('crawl/start/', views.start_crawl, name='start_crawl'),
    path('crawl/status/<str:task_id>/', views.get_crawl_status, name='crawl_status'),
    path('crawl/tasks/', views.list_crawl_tasks, name='list_crawl_tasks'),
    
    # ========== 图片上传 ==========
    path('images/upload/', views.upload_image, name='upload_image'),
    
    # ========== 任务结果上报 ==========
    path('tasks/<str:task_id>/result/', views.report_task_result, name='report_task_result'),
    
    # ========== 成员A专用接口 ==========
    path('seeds/pending/', views.get_pending_seeds, name='pending_seeds'),
    path('seeds/status/', views.update_seed_status, name='update_seed_status'),
    
    # ========== 爬虫配置接口 ==========
    # 统一使用 get_crawler_config_from_db，保留两个路由名便于兼容
    path('crawler/config/', views.get_crawler_config_from_db, name='crawler_config'),
    path('crawler/config/db/', views.get_crawler_config_from_db, name='crawler_config_db'),
]