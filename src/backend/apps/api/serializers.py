"""
功能：数据序列化器（JSON 格式转换）- V2.0
"""

from rest_framework import serializers
from .models import PageSnapshot, SeedURL, CrawlTask, Template, User, UserTemplateHistory


class PageSnapshotSerializer(serializers.ModelSerializer):
    """网页快照的序列化器 - V2.0"""
    
    process_status_display = serializers.CharField(source='get_process_status_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    
    class Meta:
        model = PageSnapshot
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'content_hash', 'version')


class SeedURLSerializer(serializers.ModelSerializer):
    """种子URL的序列化器 - V2.0"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SeedURL
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class CrawlTaskSerializer(serializers.ModelSerializer):
    """爬虫任务序列化器 - V2.0（含新增字段）"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True, default=None)
    
    class Meta:
        model = CrawlTask
        fields = [
            'task_id', 'task_name', 'task_type', 'task_type_display',
            'generated_rule', 'template', 'template_name',
            'seed_url', 'max_depth', 'status', 'status_display',
            'total_pages', 'success_pages', 'failed_pages',
            'error_message', 'traceback', 'report',
            'created_at', 'updated_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ('task_id', 'created_at', 'updated_at')


class TemplateSerializer(serializers.ModelSerializer):
    """模板序列化器 - V2.0（含新增字段）"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)
    
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'seed_url', 'tags', 'description',
            'category', 'category_display',
            'ai_model', 'ai_api_url', 'ai_api_key', 'user_prompt',
            'ai_prompt',  # 保留兼容旧版
            'config', 'usage_count', 'is_public', 'status', 'status_display',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'usage_count', 'created_at', 'updated_at')
        extra_kwargs = {
            'ai_api_key': {'write_only': True},  # API密钥不返回给前端
        }


class TemplateListSerializer(serializers.ModelSerializer):
    """模板列表序列化器（精简版）"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'seed_url', 'tags', 'category', 'category_display',
            'ai_model', 'user_prompt', 'usage_count', 'created_at'
        ]


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserTemplateHistorySerializer(serializers.ModelSerializer):
    """用户历史模板序列化器"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_category = serializers.CharField(source='template.category', read_only=True)
    template_category_display = serializers.CharField(source='template.get_category_display', read_only=True)
    
    class Meta:
        model = UserTemplateHistory
        fields = ['id', 'template', 'template_name', 'template_category', 
                  'template_category_display', 'used_at']
        read_only_fields = ['id', 'used_at']


# ========== 请求/响应专用序列化器 ==========

class StartTaskSerializer(serializers.Serializer):
    """启动任务请求序列化器"""
    template_id = serializers.IntegerField(required=False, allow_null=True)
    seed_url = serializers.URLField(required=False, allow_blank=True)
    task_type = serializers.ChoiceField(choices=['preview', 'formal'], default='formal')
    user_prompt = serializers.CharField(required=False, allow_blank=True)
    ai_model = serializers.CharField(default='qwen2:7b', required=False)
    ai_api_url = serializers.URLField(default='http://127.0.0.1:11434', required=False)
    ai_api_key = serializers.CharField(required=False, allow_blank=True)
    config = serializers.DictField(default=dict, required=False)
    
    def validate(self, data):
        if not data.get('template_id') and not data.get('seed_url'):
            raise serializers.ValidationError("template_id 或 seed_url 至少提供一个")
        return data


class GenerateRulesSerializer(serializers.Serializer):
    """生成采集规则请求序列化器"""
    ai_model = serializers.CharField(default='qwen2:7b', required=False)
    ai_api_url = serializers.URLField(default='http://127.0.0.1:11434', required=False)
    user_prompt = serializers.CharField(required=True)
    html_skeleton = serializers.CharField(required=True)


class CleanStatusSerializer(serializers.Serializer):
    """AI清洗状态上报序列化器"""
    snapshot_id = serializers.IntegerField(required=True)
    process_status = serializers.ChoiceField(choices=['ai_cleaned', 'error'], required=True)
    extracted_data = serializers.DictField(default=dict, required=False)
    error_info = serializers.CharField(required=False, allow_blank=True)


class PageSnapshotSaveSerializer(serializers.Serializer):
    """保存页面快照请求序列化器"""
    url = serializers.URLField(required=True)
    raw_html = serializers.CharField(required=False, allow_blank=True)
    markdown = serializers.CharField(required=True)
    category = serializers.CharField(required=False, allow_blank=True)
    task_id = serializers.CharField(required=False, allow_null=True)
    task_type = serializers.ChoiceField(choices=['preview', 'formal'], default='formal')
    user_prompt = serializers.CharField(required=False, allow_blank=True)
    images = serializers.ListField(default=list, required=False)