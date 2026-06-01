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
