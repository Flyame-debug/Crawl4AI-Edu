"""
功能：配置 Django 后台管理界面
用途：让管理员能在 /admin 页面可视化操作数据库
- 注册 SeedURL 和 PageSnapshot 到后台
- 配置列表显示哪些字段、搜索哪些字段、筛选哪些字段
调用方：Django Admin 自动加载
"""
# Register your models here.
from django.contrib import admin
from .models import PageSnapshot, SeedURL

@admin.register(PageSnapshot)
class PageSnapshotAdmin(admin.ModelAdmin):
    list_display = ['url', 'category', 'created_at']
    search_fields = ['url']

@admin.register(SeedURL)
class SeedURLAdmin(admin.ModelAdmin):
    list_display = ['url', 'school', 'status', 'need_render']
    search_fields = ['url', 'school']