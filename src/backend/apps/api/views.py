"""
功能：API 视图（业务逻辑）- 完整版
"""

import os
import uuid
import threading
import sys
import traceback
from pathlib import Path
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Q
from django.core.files.base import ContentFile
import base64

from .models import PageSnapshot, SeedURL, CrawlerConfig, CrawlTask
from .serializers import PageSnapshotSerializer, SeedURLSerializer
from .services import PageSnapshotService


# ==================== PageSnapshot 视图 ====================

class PageSnapshotViewSet(viewsets.ModelViewSet):
    """网页快照 API"""
    queryset = PageSnapshot.objects.all().order_by('-created_at')
    serializer_class = PageSnapshotSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(url__icontains=search) | Q(markdown__icontains=search)
            )
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        重写创建方法，使用增量更新逻辑
        支持 images 字段
        """
        url = request.data.get('url')
        markdown = request.data.get('markdown')
        
        if not url or not markdown:
            return Response(
                {'error': 'url 和 markdown 为必填字段'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 自动分类
        category = request.data.get('category')
        if not category:
            category = PageSnapshotService.auto_category_from_url(url)
        
        # 获取图片列表
        images = request.data.get('images', [])
        
        # 增量保存
        result = PageSnapshotService.save_or_update(url, markdown, category)
        
        # 更新图片字段
        if images and result['obj']:
            result['obj'].images = images
            result['obj'].save(update_fields=['images'])
        
        serializer = self.get_serializer(result['obj'])
        return Response({
            'action': result['action'],
            'data': serializer.data
        }, status=status.HTTP_201_CREATED if result['action'] == 'created' else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def auto_category(self, request):
        url = request.data.get('url')
        if not url:
            return Response({'error': 'url required'}, status=400)
        category = PageSnapshotService.auto_category_from_url(url)
        return Response({'category': category})


# ==================== SeedURL 视图 ====================

class SeedURLViewSet(viewsets.ModelViewSet):
    """种子URL API"""
    queryset = SeedURL.objects.all().order_by('-created_at')
    serializer_class = SeedURLSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        school = self.request.query_params.get('school')
        if school:
            queryset = queryset.filter(school=school)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    @action(detail=True, methods=['post'])
    def check_dead(self, request, pk=None):
        import requests
        seed = self.get_object()
        try:
            resp = requests.head(seed.url, timeout=10, allow_redirects=True)
            if resp.status_code >= 400:
                seed.status = 'failed'
                seed.save()
                return Response({'status': 'dead', 'code': resp.status_code})
            return Response({'status': 'alive', 'code': resp.status_code})
        except Exception as e:
            seed.status = 'failed'
            seed.save()
            return Response({'status': 'dead', 'error': str(e)})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = SeedURL.objects.count()
        pending = SeedURL.objects.filter(status='pending').count()
        success = SeedURL.objects.filter(status='success').count()
        failed = SeedURL.objects.filter(status='failed').count()
        return Response({
            'total': total,
            'pending': pending,
            'success': success,
            'failed': failed,
            'success_rate': round(success / total * 100, 2) if total > 0 else 0
        })


# ==================== 图片上传 API ====================

@api_view(['POST'])
def upload_image(request):
    """上传图片到 MinIO"""
    try:
        from minio import Minio
        from django.conf import settings
        import hashlib
        import base64
        import io
        
        # 获取图片数据
        if 'image' in request.FILES:
            image_data = request.FILES['image'].read()
            filename = request.FILES['image'].name
        elif request.data.get('image_base64'):
            base64_str = request.data.get('image_base64')
            if ',' in base64_str:
                base64_str = base64_str.split(',')[1]
            image_data = base64.b64decode(base64_str)
            filename = request.data.get('filename', 'image.jpg')
        else:
            return Response({'error': '请提供 image 文件或 image_base64'}, status=400)
        
        # 连接 MinIO（使用 settings 中的独立配置）
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        
        # 确保 bucket 存在
        bucket = 'crawl4ai'
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        
        # 生成文件名并上传
        file_hash = hashlib.md5(image_data).hexdigest()
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        object_name = f"images/{file_hash}.{ext}"
        
        client.put_object(
            bucket,
            object_name,
            io.BytesIO(image_data),
            len(image_data),
            content_type=f'image/{ext}'
        )
        
        # 返回访问 URL
        image_url = f"http://{settings.MINIO_ENDPOINT}/{bucket}/{object_name}"
        
        return Response({
            'success': True,
            'url': image_url,
            'image_id': file_hash,
            'filename': object_name
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# ==================== 任务结果上报 API ====================

@api_view(['POST'])
def report_task_result(request, task_id):
    """
    爬虫任务完成后上报结果
    POST /api/tasks/<task_id>/result/
    请求体: {
        "status": "completed/failed",
        "total_pages": 50,
        "success_pages": 48,
        "failed_pages": 2,
        "report": "统计信息字符串",
        "error_message": "错误信息（可选）"
    }
    """
    try:
        task = CrawlTask.objects.get(task_id=task_id)
        
        status_value = request.data.get('status', 'completed')
        total_pages = request.data.get('total_pages', 0)
        success_pages = request.data.get('success_pages', 0)
        failed_pages = request.data.get('failed_pages', 0)
        report = request.data.get('report', '')
        error_message = request.data.get('error_message', '')
        
        task.status = status_value
        task.total_pages = total_pages
        task.success_pages = success_pages
        task.failed_pages = failed_pages
        task.report = report
        if error_message:
            task.error_message = error_message
        task.updated_at = timezone.now()
        task.save()
        
        # 同时更新种子状态
        try:
            seed = SeedURL.objects.get(url=task.seed_url)
            seed.status = 'success' if status_value == 'completed' else 'failed'
            seed.save()
        except SeedURL.DoesNotExist:
            pass
        
        return Response({
            'success': True,
            'task_id': str(task.task_id),
            'status': task.status
        })
        
    except CrawlTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ==================== 配置接口 ====================

@api_view(['GET'])
def get_crawler_config_from_db(request):
    """获取爬虫配置（从数据库读取）- 成员A使用"""
    configs = CrawlerConfig.objects.filter(enabled=True)
    config_dict = {}
    for cfg in configs:
        config_dict[cfg.key] = cfg.value
    
    default_config = {
        'concurrency': 5,
        'request_delay': 1.0,
        'max_depth': 2,
        'allowed_domains': [],
        'white_list_patterns': [],
        'enable_dead_check': False,
    }
    
    for key, default_value in default_config.items():
        if key not in config_dict:
            config_dict[key] = default_value
    
    return Response(config_dict)


@api_view(['GET'])
def get_pending_seeds(request):
    """获取待爬取的种子URL列表 - 成员A使用"""
    seeds = SeedURL.objects.filter(status='pending')
    limit = int(request.query_params.get('limit', 10))
    seeds = seeds[:limit]
    
    return Response({
        'count': seeds.count(),
        'seeds': [
            {
                'id': s.id,
                'url': s.url,
                'school': s.school,
                'category': s.category,
                'need_render': s.need_render,
            }
            for s in seeds
        ]
    })


@api_view(['POST'])
def update_seed_status(request):
    """更新种子URL的爬取状态 - 成员A使用"""
    url = request.data.get('url')
    status_value = request.data.get('status')
    
    if not url:
        return Response({'error': 'url required'}, status=400)
    
    if status_value not in ['pending', 'crawling', 'success', 'failed', 'blocked']:
        return Response({'error': 'invalid status'}, status=400)
    
    try:
        seed = SeedURL.objects.get(url=url)
        seed.status = status_value
        seed.save()
        return Response({'status': 'ok', 'url': url, 'new_status': status_value})
    except SeedURL.DoesNotExist:
        return Response({'error': 'seed not found'}, status=404)


# ==================== 原有接口（保持不变）====================

import redis
from django.conf import settings

@api_view(['GET'])
def get_crawler_status(request):
    """
    爬虫状态 API - 从数据库读取，不依赖 Redis
    """
    from .models import SeedURL, CrawlTask
    
    try:
        # 种子统计
        seed_total = SeedURL.objects.count()
        seed_success = SeedURL.objects.filter(status='success').count()
        seed_failed = SeedURL.objects.filter(status='failed').count()
        seed_pending = SeedURL.objects.filter(status='pending').count()
        
        # 任务统计
        task_total = CrawlTask.objects.count()
        task_completed = CrawlTask.objects.filter(status='completed').count()
        task_running = CrawlTask.objects.filter(status='running').count()
        task_failed = CrawlTask.objects.filter(status='failed').count()
        
        return Response({
            'queue_length': 0,
            'active_workers': 0,
            'seeds': {
                'total': seed_total,
                'success': seed_success,
                'failed': seed_failed,
                'pending': seed_pending,
            },
            'tasks': {
                'total': task_total,
                'running': task_running,
                'completed': task_completed,
                'failed': task_failed,
            },
            'success_rate': round(seed_success / max(seed_total, 1) * 100, 2)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

@api_view(['GET'])
def get_logs(request):
    """获取日志"""
    lines = min(int(request.query_params.get('lines', 50)), 500)
    level = request.query_params.get('level', 'ERROR').upper()
    log_file_name = request.query_params.get('file', 'error.log')
    
    if not log_file_name.endswith('.log'):
        return Response({'error': '只支持 .log 文件'}, status=400)
    
    log_path = settings.BASE_DIR / 'logs' / log_file_name
    if not log_path.exists():
        return Response({'logs': [], 'total': 0, 'message': '日志文件不存在'})
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
        
        if level != 'ALL':
            filtered_lines = [line for line in recent_lines if f' {level} ' in line or line.startswith(level)]
            recent_lines = filtered_lines
        
        return Response({'logs': recent_lines, 'total': len(recent_lines), 'file': str(log_path)})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_log_files(request):
    """获取日志文件列表"""
    logs_dir = settings.BASE_DIR / 'logs'
    if not logs_dir.exists():
        return Response({'files': []})
    
    files = [{'name': f.name, 'size': f.stat().st_size, 'modified': f.stat().st_mtime} 
             for f in logs_dir.glob('*.log')]
    files.sort(key=lambda x: x['modified'], reverse=True)
    return Response({'files': files})


@api_view(['GET'])
def list_crawl_tasks(request):
    """列出所有爬虫任务"""
    tasks = CrawlTask.objects.all().order_by('-created_at')[:50]
    return Response({
        'total': CrawlTask.objects.count(),
        'tasks': [
            {
                'task_id': str(t.task_id),
                'status': t.status,
                'seed_url': t.seed_url,
                'total_pages': t.total_pages,
                'success_pages': t.success_pages,
                'created_at': t.created_at,
            }
            for t in tasks
        ]
    })


@api_view(['GET'])
def get_crawl_status(request, task_id):
    """查询爬虫任务状态"""
    try:
        task = CrawlTask.objects.get(task_id=task_id)
        return Response({
            'task_id': str(task.task_id),
            'status': task.status,
            'seed_url': task.seed_url,
            'max_depth': task.max_depth,
            'total_pages': task.total_pages,
            'success_pages': task.success_pages,
            'failed_pages': task.failed_pages,
            'error_message': task.error_message,
            'report': task.report,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
        })
    except CrawlTask.DoesNotExist:
        return Response({'status': 'not_found'}, status=404)


# ========== 爬虫任务控制 API ==========

import hashlib  # 新增导入

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sandbox_path = PROJECT_ROOT / "sandbox"
if str(sandbox_path) not in sys.path:
    sys.path.insert(0, str(sandbox_path))


def run_async_crawl(task_id, seed_url, max_depth, config):
    """在独立线程中运行异步爬虫"""
    try:
        import django
        django.setup()
        
        from django.utils import timezone
        from apps.api.models import CrawlTask
        
        CrawlTask.objects.filter(task_id=task_id).update(status='running')
        
        from sandbox.standalone_crawler import crawl as run_crawl
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(run_crawl(
            seed_url=seed_url,
            max_depth=max_depth,
            max_concurrent=config.get('max_concurrent', 5),
            request_delay=config.get('request_delay', 1.0),
            allowed_domains=config.get('allowed_domains', []),
            white_list_patterns=config.get('white_list_patterns', []),
            enable_dead_check=config.get('enable_dead_check', False),
        ))
        loop.close()
        
        CrawlTask.objects.filter(task_id=task_id).update(
            status='completed',
            total_pages=stats.total,
            success_pages=stats.success,
            failed_pages=stats.failed,
            report=stats.report(),
            updated_at=timezone.now()
        )
        
    except Exception as e:
        CrawlTask.objects.filter(task_id=task_id).update(
            status='failed',
            error_message=str(e),
            traceback=traceback.format_exc()
        )


@api_view(['POST'])
def start_crawl(request):
    """启动爬虫任务 API"""
    try:
        seed_url = request.data.get('seed_url')
        if not seed_url:
            return Response({'error': 'seed_url is required'}, status=400)
        
        max_depth = request.data.get('max_depth', 2)
        config = request.data.get('config', {})
        
        task = CrawlTask.objects.create(
            seed_url=seed_url,
            max_depth=max_depth,
            status='pending'
        )
        
        thread = threading.Thread(
            target=run_async_crawl,
            args=(str(task.task_id), seed_url, max_depth, config),
            daemon=True
        )
        thread.start()
        
        return Response({
            'task_id': str(task.task_id),
            'message': 'Crawl task started successfully.',
            'status_url': f'/api/crawl/status/{task.task_id}/',
            'created_at': task.created_at
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)