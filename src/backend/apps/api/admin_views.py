"""
自定义 Admin 视图
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import PageSnapshot, CrawlTask, SeedURL


@staff_member_required
def admin_dashboard(request):
    """Admin 仪表盘首页"""
    
    # 今日数据
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    today_pages = PageSnapshot.objects.filter(created_at__gte=today_start).count()
    today_tasks = CrawlTask.objects.filter(created_at__gte=today_start).count()
    
    # 系统健康度
    total_pages = PageSnapshot.objects.count()
    pages_with_data = PageSnapshot.objects.filter(
        extracted_data__isnull=False
    ).exclude(extracted_data={}).count()
    completeness = (pages_with_data / max(total_pages, 1)) * 100
    
    tasks = CrawlTask.objects.all()
    success_rate = (tasks.filter(status='completed').count() / max(tasks.count(), 1)) * 100
    
    # 最近7天趋势
    daily_stats = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))
        count = PageSnapshot.objects.filter(created_at__range=(day_start, day_end)).count()
        daily_stats.append({'date': day.strftime('%m/%d'), 'count': count})
    
    context = {
        'today_pages': today_pages,
        'today_tasks': today_tasks,
        'total_pages': total_pages,
        'completeness': round(completeness, 1),
        'success_rate': round(success_rate, 1),
        'daily_stats': daily_stats,
        'recent_tasks': tasks.order_by('-created_at')[:10],
        'recent_pages': PageSnapshot.objects.order_by('-created_at')[:10],
    }
    
    return render(request, 'admin/dashboard.html', context)