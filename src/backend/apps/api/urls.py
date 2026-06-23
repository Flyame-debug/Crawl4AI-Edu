"""
功能：API 路由配置 - V2.0
新增：历史模板接口、AI生成规则接口、AI清洗状态接口
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pagesnapshot', views.PageSnapshotViewSet, basename='pagesnapshot')
router.register(r'seedurl', views.SeedURLViewSet, basename='seedurl')

urlpatterns = [
    path('', include(router.urls)),
    
    # ==================== 公共接口 ====================
    path('crawler/status/', views.get_crawler_status, name='crawler_status'),
    path('logs/', views.get_logs, name='logs'),
    path('logs/files/', views.get_log_files, name='log_files'),
    path('stats/', views.get_dashboard_stats, name='dashboard_stats'),
    path('health/', views.health_check, name='health_check'),
    
    # ==================== 认证授权 ====================
    path('auth/login/', views.login, name='login'),
    path('auth/register/', views.register, name='register'),
    path('auth/send-code/', views.send_email_code, name='send_email_code'),
    path('auth/logout/', views.logout, name='logout'),
    
    # ==================== 成员A专用接口 ====================
    # 爬虫配置
    path('crawler/config/', views.get_crawler_config_from_db, name='crawler_config'),
    path('crawler/config/db/', views.get_crawler_config_from_db, name='crawler_config_db'),
    
    # 种子管理
    path('seeds/pending/', views.get_pending_seeds, name='pending_seeds'),
    path('seeds/status/', views.update_seed_status, name='update_seed_status'),
    
    # 图片上传
    path('images/upload/', views.upload_image, name='upload_image'),
    
    # 页面快照上报（核心接口）
    path('pagesnapshot/', views.save_page_snapshot, name='save_page_snapshot'),
    
    # 爬虫任务控制
    path('crawl/start/', views.start_crawl_task_api, name='start_crawl_api'),
    path('crawl/status/<str:task_id>/', views.get_crawl_status, name='crawl_status'),
    path('crawl/tasks/', views.list_crawl_tasks, name='list_crawl_tasks'),
    
    # 任务结果上报
    path('tasks/<str:task_id>/result/', views.report_task_result, name='report_task_result'),
    
    # ========== P2新增：AI生成采集规则（成员A专属） ==========
    path('ai/generate-rules/', views.generate_rules, name='generate_rules'),
    
    # ========== 代理接口 ==========
    path('proxy/html/', views.proxy_html, name='proxy_html'),
    
    # ==================== 成员B专用接口 ====================
    # ========== P2新增：AI清洗结果上报 ==========
    path('ai/clean-status/', views.update_clean_status, name='update_clean_status'),
    
    # ==================== 成员D专用接口（前端） ====================
    
    # ---------- 模板管理 ----------
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/update/', views.template_update, name='template_update'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/save_rule/', views.template_save_rule, name='template_save_rule'),
    # ========== P1新增：历史模板 ==========
    path('templates/history/', views.template_history, name='template_history'),
    path('templates/<int:pk>/stats/', views.template_stats, name='template_stats'),
    # ---------- 任务控制 ----------
    path('tasks/start/', views.start_task, name='start_task'),
    path('tasks/<str:task_id>/pause/', views.pause_task, name='pause_task'),
    path('tasks/<str:task_id>/stop/', views.stop_task, name='stop_task'),
    path('tasks/<str:task_id>/delete/', views.delete_task, name='delete_task'),
    path('templates/<int:pk>/review/', views.review_template, name='review_template'),
    # ---------- 任务查询 ----------
    path('tasks/', views.task_list_api, name='task_list'),
    path('tasks/<str:task_id>/detail/', views.task_detail_api, name='task_detail'),
    path('tasks/<str:task_id>/progress/', views.task_progress_api, name='task_progress'),
    path('tasks/<str:task_id>/preview/', views.task_preview_api, name='task_preview'),
    path('tasks/<str:task_id>/download/', views.task_download_api, name='task_download'),
    path('tasks/<str:task_id>/export/', views.task_export_api, name='task_export'),
]