"""
功能：配置 Django 后台管理界面
用途：让管理员能在 /admin 页面可视化操作数据库
- 注册 SeedURL 和 PageSnapshot 到后台
- 注册 CrawlerConfig 到后台（模块8.5 爬虫伦理配置）
- 配置列表显示哪些字段、搜索哪些字段、筛选哪些字段
- 添加自定义操作：批量标记状态
调用方：Django Admin 自动加载
"""

from django.contrib import admin
from .models import PageSnapshot, SeedURL, CrawlerConfig


@admin.register(PageSnapshot)
class PageSnapshotAdmin(admin.ModelAdmin):
    """网页快照后台管理"""
    list_display = ['url', 'category', 'version', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['url', 'markdown']
    readonly_fields = ['content_hash', 'created_at', 'updated_at', 'version']


@admin.register(SeedURL)
class SeedURLAdmin(admin.ModelAdmin):
    """种子URL后台管理"""
    list_display = ['url', 'school', 'category', 'status', 'need_render', 'created_at']
    list_filter = ['school', 'category', 'status', 'need_render']
    search_fields = ['url', 'school']
    actions = ['mark_as_failed', 'reset_to_pending', 'mark_as_blocked']
    
    @admin.action(description='标记为失败')
    def mark_as_failed(self, request, queryset):
        """批量标记为失败"""
        updated = queryset.update(status='failed')
        self.message_user(request, f'已标记 {updated} 个种子为失败')
    
    @admin.action(description='重置为等待中')
    def reset_to_pending(self, request, queryset):
        """重置状态为等待中"""
        updated = queryset.update(status='pending')
        self.message_user(request, f'已重置 {updated} 个种子为等待中')
    
    @admin.action(description='标记为被禁止(robots.txt)')
    def mark_as_blocked(self, request, queryset):
        """批量标记为被禁止"""
        updated = queryset.update(status='blocked')
        self.message_user(request, f'已标记 {updated} 个种子为被禁止')


@admin.register(CrawlerConfig)
class CrawlerConfigAdmin(admin.ModelAdmin):
    """
    爬虫伦理配置后台管理（模块8.5）
    用途：管理员在后台可视化配置请求延迟、并发上限等参数
    """
    list_display = ['key', 'value', 'enabled', 'updated_at']
    list_filter = ['enabled', 'updated_at']
    search_fields = ['key', 'description']
    fields = ['key', 'value', 'description', 'enabled']
    
    def get_readonly_fields(self, request, obj=None):
        """创建后 key 不可修改"""
        if obj:  # 编辑现有配置时
            return ['key']
        return []  # 新建时允许输入 key