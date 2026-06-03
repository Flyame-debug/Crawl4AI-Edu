"""
功能：Django 总路由配置
用途：把所有 URL 请求分发给对应的应用
- /admin/ -> 后台管理
- /api/ -> API 路由（pagesnapshot, seedurl 等）
- /stats/ -> 统计路由（独立，与 api 同级）
调用方：Django 启动时自动加载
"""

from django.contrib import admin
from django.urls import path, include

from apps.api.admin import admin_site

# 修改 admin 头部标题
admin.site.site_header = 'Crawl4AI 管理后台'
admin.site.site_title = 'Crawl4AI'
admin.site.index_title = '欢迎使用 Crawl4AI 教育采集系统'

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include('apps.api.urls')),      # API 路由
    path('stats/', include('apps.stats.urls')),  # 统计路由（与 api 同级）
]