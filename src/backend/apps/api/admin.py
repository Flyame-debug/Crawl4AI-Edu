"""
功能：Django 后台管理界面优化版 - V2.0
新增：Template V2.0字段支持、CrawlTask V2.0字段支持、UserTemplateHistory管理
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import PageSnapshot, SeedURL, CrawlerConfig, CrawlTask, Template, User, UserTemplateHistory

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
    """网页快照后台管理 - V2.0"""
    
    list_display = [
        'id', 'preview_url', 'category_badge', 'task_type_badge',
        'process_status_badge', 'images_count', 'created_at_ago'
    ]
    
    list_display_links = ['id', 'preview_url']
    
    list_filter = [
        'category', 'process_status', 'task_type', 'version',
        ('created_at', admin.DateFieldListFilter)
    ]
    
    search_fields = ['url', 'markdown', 'extracted_data']
    search_help_text = '搜索 URL、内容或提取的数据'
    
    readonly_fields = [
        'content_hash', 'created_at', 'updated_at', 'version',
        'url_link', 'preview_data', 'metadata_info'
    ]
    
    ordering = ['-created_at']
    list_per_page = 20
    
    actions = ['mark_as_raw_converted', 'mark_as_ai_cleaned', 'mark_as_error', 'retry_failed']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('url_link', 'category', 'task_type', 'version')
        }),
        ('内容数据', {
            'fields': ('markdown', 'raw_html', 'extracted_data'),
            'classes': ('wide',)
        }),
        ('处理状态', {
            'fields': ('process_status', 'error_info', 'processed_at'),
            'classes': ('wide',)
        }),
        ('任务关联', {
            'fields': ('task', 'user_prompt'),
            'classes': ('collapse',)
        }),
        ('元数据', {
            'fields': ('content_hash', 'images', 'metadata_info'),
            'classes': ('collapse',)
        }),
        ('错误信息', {
            'fields': ('retry_count', 'last_error'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def preview_url(self, obj):
        url = obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
        return format_html('<a href="{}" target="_blank" title="{}">{}</a>', 
                          obj.url, obj.url, url)
    preview_url.short_description = 'URL'
    
    def category_badge(self, obj):
        colors = {
            'teacher': '#28a745',
            'course': '#007bff', 
            'research': '#6f42c1',
            'news': '#fd7e14',
            'other': '#6c757d'
        }
        display_names = {
            'teacher': '👨‍🏫 教师',
            'course': '📚 课程',
            'research': '🔬 科研',
            'news': '📰 新闻',
            'other': '📄 其他'
        }
        color = colors.get(obj.category, '#6c757d')
        display = display_names.get(obj.category, obj.category or '未分类')
        return format_html('<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
                          color, display)
    category_badge.short_description = '分类'
    
    def task_type_badge(self, obj):
        if obj.task_type == 'preview':
            return format_html('<span style="background: #fd7e14; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">🔍 预览</span>')
        return format_html('<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">📦 正式</span>')
    task_type_badge.short_description = '任务类型'
    
    def process_status_badge(self, obj):
        status_config = {
            'pending': ('⏳ 待处理', '#ffc107'),
            'raw_converted': ('📝 已转Markdown', '#17a2b8'),
            'ai_cleaned': ('✨ AI已清洗', '#28a745'),
            'error': ('❌ 失败', '#dc3545'),
        }
        text, color = status_config.get(obj.process_status, ('❓ 未知', '#6c757d'))
        return format_html('<span style="color: {};">{}</span>', color, text)
    process_status_badge.short_description = '处理状态'
    
    def images_count(self, obj):
        count = len(obj.images) if obj.images else 0
        if count > 0:
            return format_html('<span style="font-weight: bold; color: #007bff;">📷 {}</span>', count)
        return '0'
    images_count.short_description = '图片'
    
    def created_at_ago(self, obj):
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + '前'
    created_at_ago.short_description = '创建时间'
    
    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank">🔗 访问页面</a>', obj.url)
    url_link.short_description = '链接'
    
    def preview_data(self, obj):
        if obj.extracted_data:
            import json
            data_preview = json.dumps(obj.extracted_data, ensure_ascii=False, indent=2)[:500]
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 300px; overflow: auto;">{}</pre>', 
                              data_preview)
        return '<span style="color: gray;">暂无提取数据</span>'
    preview_data.short_description = '数据预览'
    
    def metadata_info(self, obj):
        return format_html('''
            <table style="border-collapse: collapse;">
                <tr><td style="padding: 2px 5px;"><strong>内容哈希:</strong></td><td style="padding: 2px 5px;">{}</td></tr>
                <tr><td style="padding: 2px 5px;"><strong>页面类型:</strong></td><td style="padding: 2px 5px;">{}</td></tr>
                <tr><td style="padding: 2px 5px;"><strong>重试次数:</strong></td><td style="padding: 2px 5px;">{}</td></tr>
            </table>
        ''', (obj.content_hash or '无')[:16] + '...', obj.page_type or '未知', obj.retry_count)
    metadata_info.short_description = '元数据'
    
    # ========== 批量操作 ==========
    
    @admin.action(description='📝 标记为已转Markdown')
    def mark_as_raw_converted(self, request, queryset):
        updated = queryset.update(process_status='raw_converted', processed_at=timezone.now())
        self.message_user(request, f'已标记 {updated} 条数据为已转Markdown')
    
    @admin.action(description='✨ 标记为AI已清洗')
    def mark_as_ai_cleaned(self, request, queryset):
        updated = queryset.update(process_status='ai_cleaned', processed_at=timezone.now())
        self.message_user(request, f'已标记 {updated} 条数据为AI已清洗')
    
    @admin.action(description='❌ 标记为错误')
    def mark_as_error(self, request, queryset):
        updated = queryset.update(process_status='error')
        self.message_user(request, f'已标记 {updated} 条数据为错误')
    
    @admin.action(description='🔄 重试失败数据')
    def retry_failed(self, request, queryset):
        updated = queryset.filter(process_status='error').update(
            process_status='pending', 
            retry_count=models.F('retry_count') + 1
        )
        self.message_user(request, f'已重置 {updated} 条失败数据为待处理')


# ==================== 爬虫任务 Admin ====================
@admin.register(CrawlTask)
class CrawlTaskAdmin(BaseAdmin):
    """爬虫任务管理 - V2.0（含task_type和generated_rule）"""
    
    list_display = [
        'task_id_short', 'task_name_short', 'task_type_badge', 'status_badge', 
        'seed_url_short', 'pages_progress', 'duration', 'created_at'
    ]
    list_filter = ['status', 'task_type', ('created_at', admin.DateFieldListFilter)]
    search_fields = ['seed_url', 'task_id', 'task_name']
    readonly_fields = ['task_id', 'created_at', 'updated_at']
    list_per_page = 20
    
    fieldsets = (
        ('任务信息', {
            'fields': ('task_id', 'task_name', 'task_type', 'status', 'seed_url', 'template')
        }),
        ('AI采集规则', {
            'fields': ('generated_rule',),
            'classes': ('collapse',)
        }),
        ('爬取进度', {
            'fields': ('total_pages', 'success_pages', 'failed_pages', 'report')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('错误信息', {
            'fields': ('error_message', 'traceback'),
            'classes': ('collapse',)
        }),
    )
    
    def task_id_short(self, obj):
        return str(obj.task_id)[:8]
    task_id_short.short_description = '任务ID'
    
    def task_name_short(self, obj):
        name = obj.task_name or '-'
        return name[:30] + '...' if len(name) > 30 else name
    task_name_short.short_description = '任务名称'
    
    def task_type_badge(self, obj):
        if obj.task_type == 'preview':
            return format_html('<span style="background: #fd7e14; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">🔍 预览</span>')
        return format_html('<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">📦 正式</span>')
    task_type_badge.short_description = '类型'
    
    def status_badge(self, obj):
        config = {
            'pending': ('⏳ 等待', '#ffc107'),
            'running': ('▶️ 运行', '#17a2b8'),
            'paused': ('⏸️ 暂停', '#6c757d'),
            'stopped': ('⏹️ 停止', '#6c757d'),
            'completed': ('✅ 完成', '#28a745'),
            'failed': ('❌ 失败', '#dc3545'),
        }
        text, color = config.get(obj.status, ('❓ 未知', '#6c757d'))
        return format_html('<span style="color: {};">{}</span>', color, text)
    status_badge.short_description = '状态'
    
    def seed_url_short(self, obj):
        url = obj.seed_url[:50] + '...' if len(obj.seed_url) > 50 else obj.seed_url
        return format_html('<a href="{}" target="_blank">{}</a>', obj.seed_url, url)
    seed_url_short.short_description = '种子URL'
    
    def pages_progress(self, obj):
        total = max(obj.total_pages, 1)
        percent = int(obj.success_pages / total * 100)
        return format_html('''
            <div style="width: 100px; background: #e9ecef; border-radius: 10px; overflow: hidden;">
                <div style="width: {}%; background: #28a745; color: white; text-align: center; font-size: 11px;">{}/{}</div>
            </div>
        ''', percent, obj.success_pages, obj.total_pages or 0)
    pages_progress.short_description = '进度'
    
    # ✅ 修复 duration 方法 - 处理时区问题
    def duration(self, obj):
        """计算任务执行时长"""
        try:
            # 确定结束时间
            end_time = obj.completed_at or obj.updated_at
            
            # 如果没有开始时间或结束时间，返回 '-'
            if not obj.started_at or not end_time:
                return '-'
            
            start = obj.started_at
            end = end_time
            
            # ✅ 确保两个时间都是 offset-aware（有时区）
            if timezone.is_naive(start):
                start = timezone.make_aware(start)
            if timezone.is_naive(end):
                end = timezone.make_aware(end)
            
            # 计算时间差
            delta = end - start
            total_seconds = delta.total_seconds()
            
            # 如果时间为负数，返回 '-'
            if total_seconds < 0:
                return '-'
            
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            return f"{minutes:02d}:{seconds:02d}"
            
        except Exception as e:
            # 如果出错，返回 '-'
            return '-'
    duration.short_description = '耗时'

# ==================== 种子URL Admin ====================
@admin.register(SeedURL)
class SeedURLAdmin(BaseAdmin):
    
    list_display = ['id', 'url_short', 'school', 'category_badge', 'status_badge', 'need_render_icon', 'created_at']
    list_filter = ['school', 'category', 'status', 'need_render']
    search_fields = ['url', 'school']
    list_per_page = 20
    
    actions = ['mark_as_success', 'mark_as_failed', 'reset_to_pending']
    
    def url_short(self, obj):
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    url_short.short_description = 'URL'
    
    def category_badge(self, obj):
        colors = {
            'teacher': '#28a745', 
            'course': '#007bff', 
            'research': '#6f42c1',
            'other': '#6c757d'
        }
        display_names = {
            'teacher': '👨‍🏫 教师',
            'course': '📚 课程',
            'research': '🔬 科研',
            'other': '📄 其他'
        }
        color = colors.get(obj.category, '#6c757d')
        display = display_names.get(obj.category, obj.category or '未分类')
        return format_html('<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px;">{}</span>', color, display)
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
    """模板管理 - V2.0（含分类、AI配置字段）"""
    
    list_display = [
        'id', 'name', 'category_badge', 'seed_url_short', 
        'ai_model_short', 'tags_display', 'usage_count', 'created_at'
    ]
    list_filter = ['category', 'status', 'is_public', 'created_at']
    search_fields = ['name', 'description', 'seed_url', 'user_prompt']
    list_per_page = 20
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'seed_url', 'category', 'tags', 'description', 'status', 'is_public')
        }),
        ('AI配置', {
            'fields': ('ai_model', 'ai_api_url', 'ai_api_key', 'user_prompt'),
            'description': '配置AI模型和提取指令'
        }),
        ('兼容配置', {
            'fields': ('ai_prompt', 'config'),
            'classes': ('collapse',),
            'description': '旧版配置字段，保留兼容'
        }),
        ('统计信息', {
            'fields': ('usage_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_badge(self, obj):
        colors = {
            'teacher': '#28a745',
            'course': '#007bff',
            'news': '#fd7e14',
            'research': '#6f42c1',
            'other': '#6c757d'
        }
        display_names = {
            'teacher': '👨‍🏫 教师信息',
            'course': '📚 课程信息',
            'news': '📰 新闻公告',
            'research': '🔬 科研成果',
            'other': '📄 其他'
        }
        color = colors.get(obj.category, '#6c757d')
        display = display_names.get(obj.category, obj.category)
        return format_html('<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>', color, display)
    category_badge.short_description = '分类'
    
    def ai_model_short(self, obj):
        model = obj.ai_model or 'qwen2:7b'
        return model[:20]
    ai_model_short.short_description = 'AI模型'
    
    def seed_url_short(self, obj):
        url = obj.seed_url[:50] + '...' if len(obj.seed_url) > 50 else obj.seed_url
        return format_html('<a href="{}" target="_blank">{}</a>', obj.seed_url, url)
    seed_url_short.short_description = '种子URL'
    
    def tags_display(self, obj):
        tags = obj.tags or []
        badges = ''.join([f'<span style="background: #e9ecef; padding: 2px 6px; margin: 0 2px; border-radius: 10px; font-size: 11px;">{tag}</span>' for tag in tags[:3]])
        if len(tags) > 3:
            badges += f'<span> +{len(tags)-3}</span>'
        return format_html(badges or '<span style="color: gray;">无标签</span>')
    tags_display.short_description = '标签'


# ==================== 历史模板 Admin ====================
@admin.register(UserTemplateHistory)
class UserTemplateHistoryAdmin(BaseAdmin):
    """用户历史模板管理 - P1新增"""
    
    list_display = ['id', 'user', 'template_name', 'template_category', 'used_at']
    list_filter = ['used_at', 'template__category']
    search_fields = ['user__username', 'template__name']
    readonly_fields = ['used_at']
    list_per_page = 20
    
    def template_name(self, obj):
        return obj.template.name
    template_name.short_description = '模板名称'
    
    def template_category(self, obj):
        display_names = {
            'teacher': '👨‍🏫 教师',
            'course': '📚 课程',
            'news': '📰 新闻',
            'research': '🔬 科研',
            'other': '📄 其他'
        }
        return display_names.get(obj.template.category, obj.template.category)
    template_category.short_description = '模板分类'


# ==================== 爬虫配置 Admin ====================
@admin.register(CrawlerConfig)
class CrawlerConfigAdmin(BaseAdmin):
    
    list_display = ['key', 'value_preview', 'enabled_badge', 'updated_at']
    list_filter = ['enabled']
    search_fields = ['key', 'description']
    
    def value_preview(self, obj):
        val = str(obj.value)
        return val[:50] + '...' if len(val) > 50 else val
    value_preview.short_description = '配置值'
    
    def enabled_badge(self, obj):
        if obj.enabled:
            return format_html('<span style="color: #28a745;">✅ 启用</span>')
        return format_html('<span style="color: #6c757d;">⭕ 禁用</span>')
    enabled_badge.short_description = '状态'


# ==================== 用户 Admin ====================
@admin.register(User)
class UserAdmin(BaseAdmin):
    """用户管理"""
    list_display = ['id', 'username', 'email', 'avatar_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['username', 'email']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('username', 'email', 'avatar')
        }),
        ('认证信息', {
            'fields': ('password', 'is_active')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" style="width: 30px; height: 30px; border-radius: 50%;" />', obj.avatar)
        return '-'
    avatar_preview.short_description = '头像'


# 需要导入models以支持F表达式
from django.db import models