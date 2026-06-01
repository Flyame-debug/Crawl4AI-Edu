"""
功能：统计 API 视图
用途：提供数据统计接口，供前端监控看板使用
- GET /api/stats/ - 返回总页面数、分类统计、质量指标
调用方：被 stats/urls.py 调用
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import PageSnapshot, SeedURL


@api_view(['GET'])
def get_stats(request):
    """获取统计数据 - 供前端监控看板调用"""
    total_pages = PageSnapshot.objects.count()
    
    category_stats = {
        '师资': PageSnapshot.objects.filter(category='师资').count(),
        '课程': PageSnapshot.objects.filter(category='课程').count(),
        '科研': PageSnapshot.objects.filter(category='科研').count(),
        '其他': PageSnapshot.objects.filter(category='其他').count(),
    }
    
    seed_stats = {
        'total': SeedURL.objects.count(),
        'pending': SeedURL.objects.filter(status='pending').count(),
        'success': SeedURL.objects.filter(status='success').count(),
        'failed': SeedURL.objects.filter(status='failed').count(),
    }
    
    return Response({
        'total_pages': total_pages,
        'by_category': category_stats,
        'seed_stats': seed_stats,
    })