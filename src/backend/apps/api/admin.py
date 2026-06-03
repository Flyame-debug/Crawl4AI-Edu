"""
功能：配置 Django 后台管理界面
用途：让管理员能在 /admin 页面可视化操作数据库
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from .models import PageSnapshot, SeedURL, CrawlerConfig, CrawlTask


# ==================== 自定义 Admin 站点 ====================

class Crawl4AIAdminSite(admin.AdminSite):
    """自定义 Admin 站点"""
    site_header = 'Crawl4AI 教育采集系统'
    site_title = 'Crawl4AI 管理后台'
    index_title = '仪表盘'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('stats-dashboard/', self.admin_view(self.stats_dashboard), name='stats_dashboard'),
            path('api/stats-data/', self.admin_view(self.api_stats_data), name='api_stats_data'),
            path('api/tasks-data/', self.admin_view(self.api_tasks_data), name='api_tasks_data'),
        ]
        return custom_urls + urls
    
    def stats_dashboard(self, request):
        """统计看板页面"""
        return render(request, 'admin/stats_dashboard.html', {
            'title': '数据统计看板',
            'site_header': self.site_header,
        })
    
    def api_stats_data(self, request):
        """统计数据 API"""
        total_pages = PageSnapshot.objects.count()
        
        category_stats = {
            '师资': PageSnapshot.objects.filter(category='师资').count(),
            '课程': PageSnapshot.objects.filter(category='课程').count(),
            '科研': PageSnapshot.objects.filter(category='科研').count(),
            '其他': PageSnapshot.objects.filter(category='其他').count(),
        }
        
        seed_stats = {
            'total': SeedURL.objects.count(),
            'pending': SeedURL.objects.filter(status='pending').count(),
            'success': SeedURL.objects.filter(status='success').count(),
            'failed': SeedURL.objects.filter(status='failed').count(),
        }
        
        task_stats = {
            'total': CrawlTask.objects.count(),
            'pending': CrawlTask.objects.filter(status='pending').count(),
            'running': CrawlTask.objects.filter(status='running').count(),
            'completed': CrawlTask.objects.filter(status='completed').count(),
            'failed': CrawlTask.objects.filter(status='failed').count(),
        }
        
        # 近7天趋势
        daily_stats = []
        for i in range(7):
            day = timezone.now() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            count = PageSnapshot.objects.filter(created_at__range=(day_start, day_end)).count()
            daily_stats.insert(0, {'date': day.strftime('%m-%d'), 'count': count})
        
        return JsonResponse({
            'total_pages': total_pages,
            'by_category': category_stats,
            'seed_stats': seed_stats,
            'task_stats': task_stats,
            'trend': daily_stats,
        })
    
    def api_tasks_data(self, request):
        """任务列表 API"""
        tasks = CrawlTask.objects.all().order_by('-created_at')[:20]
        data = [{
            'id': str(t.task_id)[:8],
            'status': t.status,
            'seed_url': t.seed_url[:50],
            'total_pages': t.total_pages,
            'success_pages': t.success_pages,
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        } for t in tasks]
        return JsonResponse({'tasks': data})


# 创建 Admin 站点实例
admin_site = Crawl4AIAdminSite(name='myadmin')


# ==================== 模型注册 ====================

@admin.register(PageSnapshot, site=admin_site)
class PageSnapshotAdmin(admin.ModelAdmin):
    """网页快照后台管理"""
    list_display = ['id', 'url_short', 'category', 'version', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['url', 'markdown']
    readonly_fields = ['content_hash', 'created_at', 'updated_at', 'version']
    list_per_page = 20
    
    def url_short(self, obj):
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    url_short.short_description = 'URL'


@admin.register(SeedURL, site=admin_site)
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


@admin.register(CrawlerConfig, site=admin_site)
class CrawlerConfigAdmin(admin.ModelAdmin):
    """爬虫伦理配置后台管理"""
    list_display = ['key', 'value_preview', 'enabled', 'updated_at']
    list_filter = ['enabled', 'updated_at']
    search_fields = ['key', 'description']
    
    def value_preview(self, obj):
        val = str(obj.value)
        return val[:50] + '...' if len(val) > 50 else val
    value_preview.short_description = '配置值'


@admin.register(CrawlTask, site=admin_site)
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
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    status_color.short_description = '状态'
    
    def seed_url_short(self, obj):
        return obj.seed_url[:50] + '...' if len(obj.seed_url) > 50 else obj.seed_url
    seed_url_short.short_description = '种子URL'