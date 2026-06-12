"""
功能：数据序列化器（JSON 格式转换）
"""

from rest_framework import serializers
from .models import PageSnapshot, SeedURL, CrawlTask


class PageSnapshotSerializer(serializers.ModelSerializer):
    """网页快照的序列化器"""
    class Meta:
        model = PageSnapshot
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class SeedURLSerializer(serializers.ModelSerializer):
    """种子URL的序列化器"""
    class Meta:
        model = SeedURL
        fields = '__all__'
        read_only_fields = ('created_at',)


class CrawlTaskSerializer(serializers.ModelSerializer):
    """爬虫任务序列化器"""
    class Meta:
        model = CrawlTask
        fields = '__all__'
        read_only_fields = ('task_id', 'created_at', 'updated_at')