"""
自定义 Admin 视图 - V2.0
新增：V2.0字段统计、任务类型统计、处理状态统计
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import PageSnapshot, CrawlTask, SeedURL, Template, UserTemplateHistory


@staff_member_required
def admin_dashboard(request):
    """Admin 仪表盘首页 - V2.0"""
    
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    # ========== 今日数据 ==========
    today_pages = PageSnapshot.objects.filter(created_at__gte=today_start).count()
    today_tasks = CrawlTask.objects.filter(created_at__gte=today_start).count()
    
    # ========== 页面统计（V2.0新增） ==========
    total_pages = PageSnapshot.objects.count()
    
    # 按处理状态统计
    pages_by_status = {
        'pending': PageSnapshot.objects.filter(process_status='pending').count(),
        'raw_converted': PageSnapshot.objects.filter(process_status='raw_converted').count(),
        'ai_cleaned': PageSnapshot.objects.filter(process_status='ai_cleaned').count(),
        'error': PageSnapshot.objects.filter(process_status='error').count(),
    }
    
    # 按任务类型统计
    pages_by_task_type = {
        'preview': PageSnapshot.objects.filter(task_type='preview').count(),
        'formal': PageSnapshot.objects.filter(task_type='formal').count(),
    }
    
    # 数据完整率（有extracted_data的页面）
    pages_with_data = PageSnapshot.objects.filter(
        extracted_data__isnull=False
    ).exclude(extracted_data={}).count()
    completeness = (pages_with_data / max(total_pages, 1)) * 100
    
    # ========== 任务统计（V2.0新增） ==========
    tasks = CrawlTask.objects.all()
    tasks_completed = tasks.filter(status='completed').count()
    tasks_running = tasks.filter(status='running').count()
    tasks_paused = tasks.filter(status='paused').count()
    tasks_stopped = tasks.filter(status='stopped').count()
    tasks_failed = tasks.filter(status='failed').count()
    tasks_pending = tasks.filter(status='pending').count()
    
    # 按任务类型统计
    tasks_by_type = {
        'preview': tasks.filter(task_type='preview').count(),
        'formal': tasks.filter(task_type='formal').count(),
    }
    
    success_rate = (tasks_completed / max(tasks.count(), 1)) * 100
    
    # ========== 模板统计 ==========
    template_total = Template.objects.count()
    template_by_category = dict(
        Template.objects.values('category')
        .annotate(count=Count('id'))
        .values_list('category', 'count')
    )
    
    # 历史模板使用统计
    history_total = UserTemplateHistory.objects.count()
    history_last_week = UserTemplateHistory.objects.filter(
        used_at__gte=today_start - timedelta(days=7)
    ).count()
    
    # ========== 种子统计 ==========
    seed_total = SeedURL.objects.count()
    seed_success = SeedURL.objects.filter(status='success').count()
    seed_failed = SeedURL.objects.filter(status='failed').count()
    seed_pending = SeedURL.objects.filter(status='pending').count()
    
    # ========== 最近7天趋势（V2.0增强） ==========
    daily_stats = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))
        
        # 当天数据
        pages_count = PageSnapshot.objects.filter(created_at__range=(day_start, day_end)).count()
        formal_count = PageSnapshot.objects.filter(
            created_at__range=(day_start, day_end), 
            task_type='formal'
        ).count()
        preview_count = PageSnapshot.objects.filter(
            created_at__range=(day_start, day_end), 
            task_type='preview'
        ).count()
        
        daily_stats.append({
            'date': day.strftime('%m/%d'),
            'count': pages_count,
            'formal': formal_count,
            'preview': preview_count
        })
    
    # ========== 最近任务（含任务类型） ==========
    recent_tasks = tasks.order_by('-created_at')[:10]
    recent_tasks_list = []
    for t in recent_tasks:
        recent_tasks_list.append({
            'task_id': str(t.task_id)[:8],
            'task_name': t.task_name or '-',
            'task_type': t.task_type,
            'status': t.status,
            'seed_url': t.seed_url[:50] + '...' if len(t.seed_url) > 50 else t.seed_url,
            'pages': f"{t.success_pages}/{t.total_pages or 0}",
            'created_at': t.created_at
        })
    
    # ========== 最近页面（V2.0增强） ==========
    recent_pages = PageSnapshot.objects.select_related('task').order_by('-created_at')[:10]
    recent_pages_list = []
    for p in recent_pages:
        recent_pages_list.append({
            'url': p.url[:60] + '...' if len(p.url) > 60 else p.url,
            'category': p.category,
            'task_type': p.task_type,
            'process_status': p.process_status,
            'has_extracted': bool(p.extracted_data and p.extracted_data != {}),
            'created_at': p.created_at
        })
    
    # ========== 系统健康度 ==========
    health_status = {
        'is_healthy': completeness >= 70 and success_rate >= 80,
        'completeness': round(completeness, 1),
        'success_rate': round(success_rate, 1),
        'pending_pages': pages_by_status['pending'],
        'pending_seeds': seed_pending,
        'running_tasks': tasks_running,
    }
    
    # ========== 各分类数据量 ==========
    category_stats = dict(
        PageSnapshot.objects.values('category')
        .annotate(count=Count('id'))
        .values_list('category', 'count')
    )
    
    # 分类显示名称映射
    category_display = {
        'teacher': '👨‍🏫 教师信息',
        'course': '📚 课程信息',
        'news': '📰 新闻公告',
        'research': '🔬 科研成果',
        'other': '📄 其他'
    }
    
    category_data = [
        {'name': category_display.get(cat, cat), 'count': count}
        for cat, count in category_stats.items()
    ]
    
    context = {
        # 今日数据
        'today_pages': today_pages,
        'today_tasks': today_tasks,
        
        # 页面统计
        'total_pages': total_pages,
        'pages_by_status': pages_by_status,
        'pages_by_task_type': pages_by_task_type,
        'completeness': round(completeness, 1),
        'pages_with_data': pages_with_data,
        
        # 任务统计
        'total_tasks': tasks.count(),
        'tasks_completed': tasks_completed,
        'tasks_running': tasks_running,
        'tasks_paused': tasks_paused,
        'tasks_stopped': tasks_stopped,
        'tasks_failed': tasks_failed,
        'tasks_pending': tasks_pending,
        'tasks_by_type': tasks_by_type,
        'success_rate': round(success_rate, 1),
        
        # 模板统计
        'template_total': template_total,
        'template_by_category': template_by_category,
        'history_total': history_total,
        'history_last_week': history_last_week,
        
        # 种子统计
        'seed_total': seed_total,
        'seed_success': seed_success,
        'seed_failed': seed_failed,
        'seed_pending': seed_pending,
        
        # 趋势数据
        'daily_stats': daily_stats,
        'category_data': category_data,
        
        # 最近数据
        'recent_tasks': recent_tasks_list,
        'recent_pages': recent_pages_list,
        
        # 健康度
        'health_status': health_status,
    }
    
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def admin_task_detail(request, task_id):
    """任务详情页（V2.0增强）"""
    from django.shortcuts import get_object_or_404
    
    task = get_object_or_404(CrawlTask, task_id=task_id)
    
    # 关联的页面
    pages = PageSnapshot.objects.filter(task=task).order_by('-created_at')
    
    # 按处理状态统计
    pages_by_status = {
        'pending': pages.filter(process_status='pending').count(),
        'raw_converted': pages.filter(process_status='raw_converted').count(),
        'ai_cleaned': pages.filter(process_status='ai_cleaned').count(),
        'error': pages.filter(process_status='error').count(),
    }
    
    # 提取成功率
    extracted_count = pages.filter(
        extracted_data__isnull=False
    ).exclude(extracted_data={}).count()
    extract_rate = (extracted_count / max(pages.count(), 1)) * 100
    
    context = {
        'task': task,
        'pages': pages[:50],
        'pages_total': pages.count(),
        'pages_by_status': pages_by_status,
        'extracted_count': extracted_count,
        'extract_rate': round(extract_rate, 1),
    }
    
    return render(request, 'admin/task_detail.html', context)