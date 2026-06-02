from django.db import models

# Create your models here.
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