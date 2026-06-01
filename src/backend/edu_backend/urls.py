"""
功能：Django 总路由配置
用途：把所有 URL 请求分发给对应的应用
- /admin/ -> 后台管理
- /api/ -> API 路由（包含 pages、seeds）
- /api/stats/ -> 统计路由
调用方：Django 启动时自动加载
"""

from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse


# 修改 admin 头部标题（放在这里）
admin.site.site_header = 'Crawl4AI 管理后台'
admin.site.site_title = 'Crawl4AI'
admin.site.index_title = '欢迎使用 Crawl4AI 教育采集系统'

urlpatterns = [
    path('grappelli/', include('grappelli.urls')), 
    path("", admin.site.urls),  
    path("api/", include("apps.api.urls")),
]
