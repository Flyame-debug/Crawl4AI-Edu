"""
功能：定义数据库表结构（数据模型）- V2.0完整版
"""
import uuid
from django.db import models


class PageSnapshot(models.Model):
    """网页快照模型 - V2.0"""
    
    PROCESS_STATUS_CHOICES = [
        ('pending', '待处理'),
        ('raw_converted', '已基础转Markdown'),
        ('ai_cleaned', '已AI清洗+结构化提取'),
        ('error', '处理失败'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('preview', '预览任务'),
        ('formal', '正式采集'),
    ]
    
    PAGE_TYPE_CHOICES = [
        ('teacher', '教师'),
        ('course', '课程'),
        ('research', '科研'),
        ('news', '新闻公告'),
        ('other', '其他'),
    ]
    
    # ========== 核心字段 ==========
    url = models.URLField(verbose_name="URL地址")
    raw_html = models.TextField(blank=True, null=True, verbose_name="原始HTML")
    markdown = models.TextField(blank=True, null=True, verbose_name="Markdown内容")
    content_hash = models.CharField(max_length=64, blank=True, null=True, verbose_name="内容哈希")
    
    # ========== 状态字段 ==========
    process_status = models.CharField(
        max_length=20, 
        choices=PROCESS_STATUS_CHOICES, 
        default='pending',
        verbose_name="处理状态"
    )
    extracted_data = models.JSONField(default=dict, blank=True, null=True, verbose_name="结构化提取数据")
    error_info = models.TextField(blank=True, null=True, verbose_name="错误信息")
    
    # ========== 任务关联字段 ==========
    task_type = models.CharField(
        max_length=20, 
        choices=TASK_TYPE_CHOICES, 
        default='formal',
        verbose_name="任务类型"
    )
    user_prompt = models.TextField(blank=True, null=True, verbose_name="用户提取指令")
    task = models.ForeignKey(
        'CrawlTask', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="关联任务"
    )
    
    # ========== 分类与内容字段 ==========
    category = models.CharField(max_length=50, null=True, blank=True, verbose_name="分类")
    page_type = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=PAGE_TYPE_CHOICES,
        default='other',
        verbose_name="页面类型"
    )
    images = models.JSONField(default=list, blank=True, verbose_name="图片列表")
    
    # ========== 版本与错误处理 ==========
    version = models.IntegerField(default=1, verbose_name="版本号")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    last_error = models.TextField(blank=True, null=True, verbose_name="最后错误")
    
    # ========== 时间戳 ==========
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="处理时间")
    
    class Meta:
        db_table = 'page_snapshots'
        verbose_name = '网页快照'
        verbose_name_plural = '网页快照'
        unique_together = [['url', 'task_id']]
    
    def __str__(self):
        return self.url


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
    school = models.CharField(max_length=100, blank=True, null=True, verbose_name="所属高校")
    category = models.CharField(max_length=50, blank=True, null=True, verbose_name="分类")
    need_render = models.BooleanField(default=False, verbose_name="需要动态渲染")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    priority = models.IntegerField(default=0, verbose_name="优先级")
    retry_count = models.IntegerField(default=0, verbose_name="重试次数")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'seed_urls'
        verbose_name = '种子URL'
        verbose_name_plural = '种子URL'
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return self.url


class CrawlerConfig(models.Model):
    """爬虫配置模型"""
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
    """爬虫任务模型 - V2.0"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('paused', '已暂停'),
        ('stopped', '已停止'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('preview', '预览任务'),
        ('formal', '正式采集'),
    ]
    
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="任务ID")
    task_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="任务名称")
    
    # V2.0 新增字段
    task_type = models.CharField(
        max_length=20, 
        choices=TASK_TYPE_CHOICES, 
        default='formal',
        verbose_name="任务类型"
    )
    generated_rule = models.TextField(blank=True, null=True, verbose_name="AI生成的采集规则")
    
    # 关联字段
    template = models.ForeignKey(
        'Template', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="关联模板"
    )
    
    # 任务字段
    seed_url = models.URLField(verbose_name="种子URL")
    max_depth = models.IntegerField(default=2, verbose_name="最大深度")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    
    # 统计字段
    total_pages = models.IntegerField(default=0, verbose_name="总页面数")
    success_pages = models.IntegerField(default=0, verbose_name="成功页面数")
    failed_pages = models.IntegerField(default=0, verbose_name="失败页面数")
    
    # 错误字段
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    traceback = models.TextField(blank=True, null=True, verbose_name="错误堆栈")
    report = models.TextField(blank=True, null=True, verbose_name="爬虫报告")
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    started_at = models.DateTimeField(blank=True, null=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="完成时间")
    
    class Meta:
        db_table = 'crawl_tasks'
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_id} - {self.status}"


class Template(models.Model):
    """爬取模板 - V2.0"""
    
    CATEGORY_CHOICES = [
        ('teacher', '教师信息'),
        ('course', '课程信息'),
        ('news', '新闻公告'),
        ('research', '科研成果'),
        ('other', '其他'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已驳回'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="模板名称")
    seed_url = models.URLField(verbose_name="种子URL")
    tags = models.JSONField(default=list, blank=True, verbose_name="标签列表")
    description = models.TextField(blank=True, verbose_name="模板描述")
    config = models.JSONField(default=dict, verbose_name="爬虫配置")
    
    # V2.0 新增字段
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        default='other',
        verbose_name="模板分类"
    )
    ai_model = models.CharField(max_length=100, default='qwen2:7b', verbose_name="AI模型")
    ai_api_url = models.URLField(default='http://127.0.0.1:11434', verbose_name="AI服务地址")
    ai_api_key = models.CharField(max_length=200, blank=True, null=True, verbose_name="API密钥")
    user_prompt = models.TextField(blank=True, verbose_name="用户提取指令")
    crawler_rule = models.TextField(
        blank=True, 
        null=True, 
        default='',
        verbose_name='爬虫采集规则（XPath/CSS）'
    )
    rule_generated_at = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name='规则生成时间'
    )
    # 原有字段
    ai_prompt = models.TextField(blank=True, verbose_name="AI提示词（旧，保留兼容）")
    usage_count = models.IntegerField(default=0, verbose_name="使用次数")
    is_public = models.BooleanField(default=True, verbose_name="是否公开")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='approved',
        verbose_name="审核状态"
    )
    created_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'templates'
        verbose_name = '爬取模板'
        verbose_name_plural = '爬取模板'
        ordering = ['-usage_count', '-created_at']
    
    def __str__(self):
        return self.name


class User(models.Model):
    """用户模型"""
    username = models.CharField(max_length=50, unique=True, verbose_name="用户名")
    password = models.CharField(max_length=128, verbose_name="密码哈希")
    email = models.EmailField(blank=True, null=True, verbose_name="邮箱")
    avatar = models.URLField(blank=True, null=True, verbose_name="头像")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    token = models.CharField(max_length=128, blank=True, null=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return self.username


class UserTemplateHistory(models.Model):
    """用户历史模板记录 - V2.0 P1新增"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    template = models.ForeignKey(Template, on_delete=models.CASCADE, verbose_name="模板")
    used_at = models.DateTimeField(auto_now_add=True, verbose_name="使用时间")
    
    class Meta:
        db_table = 'user_template_history'
        verbose_name = '用户历史模板'
        verbose_name_plural = '用户历史模板'
        unique_together = [['user', 'template']]
        ordering = ['-used_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"