"""
功能：Django 后台管理界面优化版
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import PageSnapshot, SeedURL, CrawlerConfig, CrawlTask, Template, User


# ==================== 通用配置 ====================
class BaseAdmin(admin.ModelAdmin):
    """基础Admin类，提供通用功能"""
    show_full_result_count = True
    actions_on_top = True
    actions_on_bottom = True
    list_per_page = 25


# ==================== 仪表盘首页 ====================
admin.site.site_header = 'Crawl4AI 爬虫管理系统'
admin.site.site_title = 'Crawl4AI'
admin.site.index_title = '数据仪表盘'


# ==================== 网页快照 Admin ====================
@admin.register(PageSnapshot)
class PageSnapshotAdmin(BaseAdmin):
    """网页快照后台管理 - 优化版"""
    
    # 列表显示字段（修复：添加 category 到 list_display）
    list_display = [
        'id', 'preview_url', 'category_badge', 'images_count', 
        'version', 'process_status_badge', 'created_at_ago'
    ]
    
    # 可点击链接
    list_display_links = ['id', 'preview_url']
    
    # 筛选器
    list_filter = [
        'category', 'process_status', 'version', 
        ('created_at', admin.DateFieldListFilter)
    ]
    
    # 搜索字段
    search_fields = ['url', 'markdown', 'extracted_data']
    search_help_text = '搜索 URL、内容或提取的数据'
    
    # 只读字段
    readonly_fields = [
        'content_hash', 'created_at', 'updated_at', 'version',
        'url_link', 'preview_data', 'metadata_info'
    ]
    
    # 排序
    ordering = ['-created_at']
    
    # 分页
    list_per_page = 20
    
    # 批量操作
    actions = ['mark_as_processed', 'mark_as_pending', 'retry_failed']
    
    # 字段分组（详情页）
    fieldsets = (
        ('基本信息', {
            'fields': ('url_link', 'category', 'version')
        }),
        ('内容数据', {
            'fields': ('markdown', 'raw_html', 'extracted_data'),
            'classes': ('wide',)
        }),
        ('处理状态', {
            'fields': ('process_status', 'processed_at'),
            'classes': ('collapse',)
        }),
        ('元数据', {
            'fields': ('content_hash', 'images', 'metadata_info'),
            'classes': ('collapse',)
        }),
        ('错误信息', {
            'fields': ('retry_count', 'last_error', 'process_error'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # ========== 自定义显示方法 ==========
    
    def preview_url(self, obj):
        """短链接预览"""
        url = obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
        return format_html('<a href="{}" target="_blank" title="{}">{}</a>', 
                          obj.url, obj.url, url)
    preview_url.short_description = 'URL'
    
    def category_badge(self, obj):
        """分类徽章"""
        colors = {
            '师资': '#28a745',
            '课程': '#007bff', 
            '科研': '#6f42c1',
            '其他': '#6c757d'
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html('<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
                          color, obj.category or '未分类')
    category_badge.short_description = '分类'
    
    def process_status_badge(self, obj):
        """处理状态徽章"""
        status_config = {
            'pending': ('⏳ 待处理', '#ffc107'),
            'processing': ('🔄 处理中', '#17a2b8'),
            'completed': ('✅ 已完成', '#28a745'),
            'failed': ('❌ 失败', '#dc3545'),
        }
        text, color = status_config.get(obj.process_status, ('❓ 未知', '#6c757d'))
        return format_html('<span style="color: {};">{}</span>', color, text)
    process_status_badge.short_description = '状态'
    
    def images_count(self, obj):
        """图片数量"""
        count = len(obj.images) if obj.images else 0
        if count > 0:
            return format_html('<span style="font-weight: bold; color: #007bff;">📷 {}</span>', count)
        return '0'
    images_count.short_description = '图片'
    
    def created_at_ago(self, obj):
        """相对时间"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + '前'
    created_at_ago.short_description = '创建时间'
    
    def url_link(self, obj):
        """详情页链接"""
        return format_html('<a href="{}" target="_blank">🔗 访问页面</a>', obj.url)
    url_link.short_description = '链接'
    
    def preview_data(self, obj):
        """预览提取的数据"""
        if obj.extracted_data:
            import json
            data_preview = json.dumps(obj.extracted_data, ensure_ascii=False, indent=2)[:500]
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 300px; overflow: auto;">{}</pre>', 
                              data_preview)
        return '<span style="color: gray;">暂无提取数据</span>'
    preview_data.short_description = '数据预览'
    
    def metadata_info(self, obj):
        """元数据信息"""
        return format_html('''
            <table style="border-collapse: collapse;">
                <tr><td style="padding: 2px 5px;"><strong>内容哈希:</strong></td><td style="padding: 2px 5px;">{}</td></tr>
                <tr><td style="padding: 2px 5px;"><strong>页面类型:</strong></td><td style="padding: 2px 5px;">{}</td></tr>
                <tr><td style="padding: 2px 5px;"><strong>重试次数:</strong></td><td style="padding: 2px 5px;">{}</td></tr>
            </table>
        ''', obj.content_hash[:16] + '...', obj.page_type or '未知', obj.retry_count)
    metadata_info.short_description = '元数据'
    
    # ========== 批量操作 ==========
    
    @admin.action(description='✅ 标记为已处理')
    def mark_as_processed(self, request, queryset):
        updated = queryset.update(process_status='completed', processed_at=timezone.now())
        self.message_user(request, f'已标记 {updated} 条数据为已完成')
    
    @admin.action(description='⏳ 标记为待处理')
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(process_status='pending', retry_count=0)
        self.message_user(request, f'已重置 {updated} 条数据为待处理')
    
    @admin.action(description='🔄 重试失败数据')
    def retry_failed(self, request, queryset):
        updated = queryset.filter(process_status='failed').update(process_status='pending')
        self.message_user(request, f'已重置 {updated} 条失败数据为待处理')


# ==================== 爬虫任务 Admin ====================
@admin.register(CrawlTask)
class CrawlTaskAdmin(BaseAdmin):
    """爬虫任务管理"""
    
    # 修复：移除不存在的 created_at_ago，使用 created_at
    list_display = [
        'task_id_short', 'status_badge', 'seed_url_short', 
        'pages_progress', 'duration', 'created_at'
    ]
    list_filter = ['status', ('created_at', admin.DateFieldListFilter)]
    search_fields = ['seed_url', 'task_id']
    readonly_fields = ['task_id', 'created_at', 'updated_at']
    list_per_page = 20
    
    fieldsets = (
        ('任务信息', {
            'fields': ('task_id', 'status', 'seed_url')
        }),
        ('爬取进度', {
            'fields': ('total_pages', 'success_pages', 'failed_pages', 'report')
        }),
        ('错误信息', {
            'fields': ('error_message', 'traceback'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def task_id_short(self, obj):
        return str(obj.task_id)[:8]
    task_id_short.short_description = '任务ID'
    
    def status_badge(self, obj):
        config = {
            'pending': ('⏳', '#ffc107'),
            'running': ('▶️', '#17a2b8'),
            'completed': ('✅', '#28a745'),
            'failed': ('❌', '#dc3545'),
        }
        icon, color = config.get(obj.status, ('❓', '#6c757d'))
        return format_html('<span style="color: {};">{} {}</span>', color, icon, obj.get_status_display())
    status_badge.short_description = '状态'
    
    def seed_url_short(self, obj):
        url = obj.seed_url[:50] + '...' if len(obj.seed_url) > 50 else obj.seed_url
        return format_html('<a href="{}" target="_blank">{}</a>', obj.seed_url, url)
    seed_url_short.short_description = '种子URL'
    
    def pages_progress(self, obj):
        """进度条"""
        total = max(obj.total_pages, 1)
        percent = int(obj.success_pages / total * 100)
        return format_html('''
            <div style="width: 100px; background: #e9ecef; border-radius: 10px; overflow: hidden;">
                <div style="width: {}%; background: #28a745; color: white; text-align: center; font-size: 11px;">{}/{}</div>
            </div>
        ''', percent, obj.success_pages, obj.total_pages or 0)
    pages_progress.short_description = '进度'
    
    def duration(self, obj):
        if obj.created_at and obj.updated_at:
            delta = obj.updated_at - obj.created_at
            minutes = int(delta.total_seconds() // 60)
            seconds = int(delta.total_seconds() % 60)
            return f"{minutes}:{seconds:02d}"
        return '-'
    duration.short_description = '耗时'


# ==================== 种子URL Admin ====================
@admin.register(SeedURL)
class SeedURLAdmin(BaseAdmin):
    # 修复：移除 list_editable，改为在详情页编辑
    list_display = ['id', 'url_short', 'school', 'category_badge', 'status_badge', 'need_render_icon', 'created_at']
    list_filter = ['school', 'category', 'status', 'need_render']
    search_fields = ['url', 'school']
    list_per_page = 20
    
    actions = ['mark_as_success', 'mark_as_failed', 'reset_to_pending']
    
    def url_short(self, obj):
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    url_short.short_description = 'URL'
    
    def category_badge(self, obj):
        colors = {'师资': '#28a745', '课程': '#007bff', '科研': '#6f42c1'}
        color = colors.get(obj.category, '#6c757d')
        return format_html('<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px;">{}</span>', color, obj.category)
    category_badge.short_description = '分类'
    
    def status_badge(self, obj):
        config = {
            'pending': ('⏳ 待处理', '#ffc107'),
            'crawling': ('🔄 爬取中', '#17a2b8'),
            'success': ('✅ 成功', '#28a745'),
            'failed': ('❌ 失败', '#dc3545'),
            'blocked': ('🚫 被禁止', '#6c757d'),
        }
        text, color = config.get(obj.status, ('❓ 未知', '#6c757d'))
        return format_html('<span style="color: {};">{}</span>', color, text)
    status_badge.short_description = '状态'
    
    def need_render_icon(self, obj):
        return '🎭 是' if obj.need_render else '📄 否'
    need_render_icon.short_description = '动态渲染'
    
    @admin.action(description='✅ 标记为成功')
    def mark_as_success(self, request, queryset):
        updated = queryset.update(status='success')
        self.message_user(request, f'已标记 {updated} 个种子为成功')
    
    @admin.action(description='❌ 标记为失败')
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'已标记 {updated} 个种子为失败')
    
    @admin.action(description='🔄 重置为待处理')
    def reset_to_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'已重置 {updated} 个种子')


# ==================== 模板 Admin ====================
@admin.register(Template)
class TemplateAdmin(BaseAdmin):
    list_display = ['id', 'name', 'seed_url_short', 'tags_display', 'usage_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description', 'seed_url']
    list_per_page = 20
    
    def seed_url_short(self, obj):
        return obj.seed_url[:50] + '...' if len(obj.seed_url) > 50 else obj.seed_url
    seed_url_short.short_description = '种子URL'
    
    def tags_display(self, obj):
        tags = obj.tags or []
        badges = ''.join([f'<span style="background: #e9ecef; padding: 2px 6px; margin: 0 2px; border-radius: 10px; font-size: 11px;">{tag}</span>' for tag in tags[:3]])
        if len(tags) > 3:
            badges += f'<span> +{len(tags)-3}</span>'
        return format_html(badges or '<span style="color: gray;">无标签</span>')
    tags_display.short_description = '标签'


# ==================== 爬虫配置 Admin ====================
@admin.register(CrawlerConfig)
class CrawlerConfigAdmin(BaseAdmin):
    # 修复：添加 enabled 到 list_display
    list_display = ['key', 'value_preview', 'enabled_badge', 'updated_at']
    list_filter = ['enabled']
    search_fields = ['key', 'description']
    # 移除 list_editable，通过编辑页修改
    
    def value_preview(self, obj):
        val = str(obj.value)
        return val[:50] + '...' if len(val) > 50 else val
    value_preview.short_description = '配置值'
    
    def enabled_badge(self, obj):
        if obj.enabled:
            return format_html('<span style="color: #28a745;">✅ 启用</span>')
        return format_html('<span style="color: #6c757d;">⭕ 禁用</span>')
    enabled_badge.short_description = '状态'


# ==================== 用户 Admin（可选）====================
@admin.register(User)
class UserAdmin(BaseAdmin):
    list_display = ['id', 'username', 'email', 'created_at']
    search_fields = ['username', 'email']
    readonly_fields = ['created_at']
    list_per_page = 20