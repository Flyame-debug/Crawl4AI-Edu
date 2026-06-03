"""
功能：配置 Django 后台管理界面
"""

from django.contrib import admin
from .models import PageSnapshot, SeedURL, CrawlerConfig, CrawlTask


@admin.register(PageSnapshot)
class PageSnapshotAdmin(admin.ModelAdmin):
    """网页快照后台管理"""
    list_display = ['id', 'url_short', 'category', 'images_count', 'version', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['url', 'markdown']
    readonly_fields = ['content_hash', 'created_at', 'updated_at', 'version']
    list_per_page = 20
    
    def url_short(self, obj):
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    url_short.short_description = 'URL'
    
    def images_count(self, obj):
        return len(obj.images) if obj.images else 0
    images_count.short_description = '图片数'


@admin.register(SeedURL)
class SeedURLAdmin(admin.ModelAdmin):
    """种子URL后台管理"""
    list_display = ['id', 'url_short', 'school', 'category', 'status', 'need_render', 'created_at']
    list_filter = ['school', 'category', 'status', 'need_render']
    search_fields = ['url', 'school']
    list_editable = ['status']
    actions = ['mark_as_failed', 'reset_to_pending', 'mark_as_blocked']
    
    def url_short(self, obj):
        return obj.url[:50] + '...' if len(obj.url) > 50 else obj.url
    url_short.short_description = 'URL'
    
    @admin.action(description='标记为失败')
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'已标记 {updated} 个种子为失败')
    
    @admin.action(description='重置为等待中')
    def reset_to_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'已重置 {updated} 个种子为等待中')
    
    @admin.action(description='标记为被禁止')
    def mark_as_blocked(self, request, queryset):
        updated = queryset.update(status='blocked')
        self.message_user(request, f'已标记 {updated} 个种子为被禁止')


@admin.register(CrawlerConfig)
class CrawlerConfigAdmin(admin.ModelAdmin):
    """爬虫配置后台管理"""
    list_display = ['key', 'value_preview', 'enabled', 'updated_at']
    list_filter = ['enabled', 'updated_at']
    search_fields = ['key', 'description']
    
    def value_preview(self, obj):
        val = str(obj.value)
        return val[:50] + '...' if len(val) > 50 else val
    value_preview.short_description = '配置值'


@admin.register(CrawlTask)
class CrawlTaskAdmin(admin.ModelAdmin):
    """爬虫任务后台管理"""
    list_display = ['task_id_short', 'status_color', 'seed_url_short', 'total_pages', 'success_pages', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['seed_url', 'task_id']
    readonly_fields = ['task_id', 'created_at', 'updated_at', 'report']
    list_per_page = 20
    
    def task_id_short(self, obj):
        return str(obj.task_id)[:8]
    task_id_short.short_description = '任务ID'
    
    def status_color(self, obj):
        colors = {'pending': 'gray', 'running': 'blue', 'completed': 'green', 'failed': 'red'}
        color = colors.get(obj.status, 'black')
        from django.utils.html import format_html
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    status_color.short_description = '状态'
    
    def seed_url_short(self, obj):
        return obj.seed_url[:50] + '...' if len(obj.seed_url) > 50 else obj.seed_url
    seed_url_short.short_description = '种子URL'