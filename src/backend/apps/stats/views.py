"""
功能：统计 API 视图
用途：提供数据统计接口，供前端监控看板使用
- GET /api/stats/ - 返回总页面数、分类统计、质量指标
调用方：被 stats/urls.py 调用
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.api.models import PageSnapshot, SeedURL  # 修改这里：添加 apps. 前缀


@api_view(['GET'])
def get_stats(request):
    """获取统计数据 - 供前端监控看板调用"""
    total_pages = PageSnapshot.objects.count()
    
    # 分类统计
    category_stats = {
        '师资': PageSnapshot.objects.filter(category='师资').count(),
        '课程': PageSnapshot.objects.filter(category='课程').count(),
        '科研': PageSnapshot.objects.filter(category='科研').count(),
        '其他': PageSnapshot.objects.filter(category='其他').count(),
    }
    
    # 种子统计
    seed_stats = {
        'total': SeedURL.objects.count(),
        'pending': SeedURL.objects.filter(status='pending').count(),
        'success': SeedURL.objects.filter(status='success').count(),
        'failed': SeedURL.objects.filter(status='failed').count(),
    }
    
    # 质量指标：字段完整率（这里用有内容的页面占比）
    total_with_content = PageSnapshot.objects.exclude(markdown='').count()
    completeness_rate = round(total_with_content / total_pages * 100, 2) if total_pages > 0 else 0
    
    # 抓取失败率
    total_seeds = SeedURL.objects.count()
    failed_seeds = SeedURL.objects.filter(status='failed').count()
    failure_rate = round(failed_seeds / total_seeds * 100, 2) if total_seeds > 0 else 0
    
    return Response({
        'total_pages': total_pages,
        'by_category': category_stats,
        'seed_stats': seed_stats,
        'quality': {
            'completeness_rate': completeness_rate,
            'failure_rate': failure_rate
        }
    })