"""
功能：数据序列化器（JSON 格式转换）
用途：把数据库里的对象转换成 JSON 格式，供 API 返回给前端
调用方：被 views.py 调用，在返回 API 响应时使用
"""

from rest_framework import serializers
from .models import PageSnapshot, SeedURL


class PageSnapshotSerializer(serializers.ModelSerializer):
    """网页快照的序列化器 - 把 PageSnapshot 对象转成 JSON"""
    
    class Meta:
        model = PageSnapshot
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class SeedURLSerializer(serializers.ModelSerializer):
    """种子URL的序列化器 - 把 SeedURL 对象转成 JSON"""
    
    class Meta:
        model = SeedURL
        fields = '__all__'
        read_only_fields = ('created_at',)
        
        
# apps/api/serializers.py 中添加

from .models import CrawlTask

class CrawlTaskSerializer(serializers.ModelSerializer):
    """爬虫任务序列化器"""
    
    class Meta:
        model = CrawlTask
        fields = '__all__'
        read_only_fields = ('task_id', 'created_at', 'updated_at')