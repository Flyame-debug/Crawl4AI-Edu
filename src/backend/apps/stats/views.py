"""
功能：统计 API 视图
用途：提供数据统计接口，供前端监控看板使用
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.api.models import PageSnapshot, SeedURL, CrawlTask


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
    
    task_stats = {
        'total': CrawlTask.objects.count(),
        'pending': CrawlTask.objects.filter(status='pending').count(),
        'running': CrawlTask.objects.filter(status='running').count(),
        'completed': CrawlTask.objects.filter(status='completed').count(),
        'failed': CrawlTask.objects.filter(status='failed').count(),
    }
    
    total_with_content = PageSnapshot.objects.exclude(markdown='').count()
    completeness_rate = round(total_with_content / total_pages * 100, 2) if total_pages > 0 else 0
    
    total_seeds = SeedURL.objects.count()
    failed_seeds = SeedURL.objects.filter(status='failed').count()
    failure_rate = round(failed_seeds / total_seeds * 100, 2) if total_seeds > 0 else 0
    
    return Response({
        'total_pages': total_pages,
        'by_category': category_stats,
        'seed_stats': seed_stats,
        'task_stats': task_stats,
        'quality': {
            'completeness_rate': completeness_rate,
            'failure_rate': failure_rate
        }
    })


@api_view(['GET'])
def get_task_detail(request, task_id):
    """获取任务详情"""
    try:
        task = CrawlTask.objects.get(task_id=task_id)
        return Response({
            'task_id': str(task.task_id),
            'status': task.status,
            'seed_url': task.seed_url,
            'total_pages': task.total_pages,
            'success_pages': task.success_pages,
            'failed_pages': task.failed_pages,
            'error_message': task.error_message,
            'report': task.report,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
        })
    except CrawlTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)