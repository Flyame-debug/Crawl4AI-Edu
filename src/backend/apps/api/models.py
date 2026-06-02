"""
功能：定义数据库表结构（数据模型）
用途：告诉 Django 数据库里要存什么数据
- PageSnapshot：网页快照表，存爬取后的 Markdown 内容
- SeedURL：种子 URL 表，存要爬取的网站地址列表
- CrawlerConfig：爬虫伦理配置表（新增）
调用方：Django 自动调用，用于创建数据库表
"""

from django.db import models

class PageSnapshot(models.Model):
    """网页快照模型"""
    url = models.URLField(unique=True, verbose_name="URL地址")
    markdown = models.TextField(verbose_name="Markdown内容")
    content_hash = models.CharField(max_length=64, verbose_name="内容哈希")
    category = models.CharField(max_length=50, null=True, blank=True, verbose_name="分类")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    version = models.IntegerField(default=1, verbose_name="版本号")
    
    class Meta:
        db_table = 'page_snapshots'
        verbose_name = '网页快照'
        verbose_name_plural = '网页快照'
    
    def __str__(self):
        return self.url

class SeedURL(models.Model):
    """种子URL模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('crawling', '爬取中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('blocked', '被禁止'),  # 新增：被 robots.txt 禁止抓取
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
    """
    爬虫伦理配置模型 - 用于模块8.5 请求伦理审查
    用途：在 Django Admin 中可视化配置爬虫的请求延迟、并发上限等参数
    调用方：成员 A 的 Celery 任务在抓取前读取此配置
    """
    
    # 配置键名（唯一标识）
    key = models.CharField(max_length=100, unique=True, verbose_name="配置键")
    
    # 配置值（JSON 格式存储，支持多种数据类型）
    value = models.JSONField(verbose_name="配置值", help_text="支持字符串、数字、布尔值、对象")
    
    # 配置描述
    description = models.CharField(max_length=255, blank=True, verbose_name="配置说明")
    
    # 是否启用
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    
    # 更新时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'crawler_configs'
        verbose_name = '爬虫配置'
        verbose_name_plural = '爬虫配置'
    
    def __str__(self):
        return f"{self.key} = {self.value}"