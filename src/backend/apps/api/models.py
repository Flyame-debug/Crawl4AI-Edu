"""
功能：定义数据库表结构（数据模型）
"""

import uuid
from django.db import models


class PageSnapshot(models.Model):
    """网页快照模型"""
    # 原有字段
    url = models.URLField(unique=True, verbose_name="URL地址")
    markdown = models.TextField(verbose_name="Markdown内容")
    content_hash = models.CharField(max_length=64, verbose_name="内容哈希")
    category = models.CharField(max_length=50, null=True, blank=True, verbose_name="分类")
    images = models.JSONField(default=list, blank=True, verbose_name="图片列表")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    version = models.IntegerField(default=1, verbose_name="版本号")
    
    # 你已添加的字段
    raw_html = models.TextField(blank=True, null=True, verbose_name="原始HTML")
    extracted_data = models.JSONField(default=dict, blank=True, verbose_name="提取数据")
    process_status = models.CharField(
        max_length=20, 
        default='pending',
        choices=[
            ('pending', '待处理'),
            ('processing', '处理中'),
            ('completed', '已完成'),
            ('failed', '失败'),
        ],
        verbose_name="处理状态"
    )
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="处理时间")
    
    # 新增字段
    page_type = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[
            ('teacher', '教师'),
            ('course', '课程'),
            ('research', '科研'),
            ('unknown', '未知'),
        ],
        verbose_name="页面类型"
    )
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    last_error = models.TextField(blank=True, null=True, verbose_name="最后错误")
    process_error = models.TextField(blank=True, null=True, verbose_name="处理错误")
    
    class Meta:
        db_table = 'page_snapshots'
        verbose_name = '网页快照'
        verbose_name_plural = '网页快照'


class SeedURL(models.Model):
    """种子URL模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('crawling', '爬取中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('blocked', '被禁止'),
    ]
    
    url = models.URLField(unique=True, verbose_name="URL地址")
    school = models.CharField(max_length=100, verbose_name="所属高校")
    category = models.CharField(max_length=50, verbose_name="分类")
    need_render = models.BooleanField(default=False, verbose_name="需要动态渲染")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        db_table = 'seed_urls'
        verbose_name = '种子URL'
        verbose_name_plural = '种子URL'
    
    def __str__(self):
        return self.url


class CrawlerConfig(models.Model):
    """爬虫伦理配置模型"""
    key = models.CharField(max_length=100, unique=True, verbose_name="配置键")
    value = models.JSONField(verbose_name="配置值", help_text="支持字符串、数字、布尔值、对象")
    description = models.CharField(max_length=255, blank=True, verbose_name="配置说明")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'crawler_configs'
        verbose_name = '爬虫配置'
        verbose_name_plural = '爬虫配置'
    
    def __str__(self):
        return f"{self.key} = {self.value}"


class CrawlTask(models.Model):
    """爬虫任务模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('paused', '已暂停'),      
        ('stopped', '已停止'),     
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="任务ID")
    seed_url = models.URLField(verbose_name="种子URL")
    max_depth = models.IntegerField(default=2, verbose_name="最大深度")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    total_pages = models.IntegerField(default=0, verbose_name="总页面数")
    success_pages = models.IntegerField(default=0, verbose_name="成功页面数")
    failed_pages = models.IntegerField(default=0, verbose_name="失败页面数")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    traceback = models.TextField(blank=True, null=True, verbose_name="错误堆栈")
    report = models.TextField(blank=True, null=True, verbose_name="爬虫报告")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'crawl_tasks'
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_id} - {self.status}"
    
    
class Template(models.Model):
    """爬取模板"""
    name = models.CharField(max_length=100, verbose_name="模板名称")
    seed_url = models.URLField(verbose_name="种子URL")
    tags = models.JSONField(default=list, blank=True, verbose_name="标签列表")
    ai_prompt = models.TextField(blank=True, verbose_name="AI提示词")
    description = models.TextField(blank=True, verbose_name="模板描述")
    config = models.JSONField(default=dict, verbose_name="爬虫配置")
    usage_count = models.IntegerField(default=0, verbose_name="使用次数")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'templates'
        verbose_name = '爬取模板'
        verbose_name_plural = '爬取模板'
    
    def __str__(self):
        return self.name


class User(models.Model):
    """用户模型（简单版，如不使用Django内置）"""
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)  # 存哈希
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
        
        
