from rest_framework import serializers
from .models import PageSnapshot, SeedURL


class PageSnapshotSerializer(serializers.ModelSerializer):
    """网页快照序列化器"""
    class Meta:
        model = PageSnapshot
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class SeedURLSerializer(serializers.ModelSerializer):
    """种子URL序列化器"""
    class Meta:
        model = SeedURL
        fields = '__all__'
        read_only_fields = ('created_at',)