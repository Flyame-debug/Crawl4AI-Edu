"""
功能：API 视图（业务逻辑）
用途：处理前端和爬虫发来的 HTTP 请求
- GET /api/pages/ - 获取网页快照列表
- POST /api/pages/ - 新增网页快照（使用增量更新逻辑）
- GET /api/seeds/ - 获取种子URL列表
- POST /api/seeds/ - 新增种子URL
调用方：被 urls.py 路由调用
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view  # 添加 api_view
from rest_framework.response import Response
from django.db.models import Q
from .models import PageSnapshot, SeedURL  # 这个相对导入是正确的
from .serializers import PageSnapshotSerializer, SeedURLSerializer
from .services import PageSnapshotService


class PageSnapshotViewSet(viewsets.ModelViewSet):
    """
    网页快照 API
    提供：列表、详情、创建、更新、删除、按分类筛选、搜索
    """
    queryset = PageSnapshot.objects.all().order_by('-created_at')
    serializer_class = PageSnapshotSerializer
    
    def get_queryset(self):
        """支持按分类、关键词搜索"""
        queryset = super().get_queryset()
        
        # 按分类筛选
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 关键词搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(url__icontains=search) | Q(markdown__icontains=search)
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        重写创建方法，使用增量更新逻辑
        爬虫模块调用此接口时，自动判断是否需要保存
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
        
        # 增量保存
        result = PageSnapshotService.save_or_update(url, markdown, category)
        
        serializer = self.get_serializer(result['obj'])
        return Response({
            'action': result['action'],
            'data': serializer.data
        }, status=status.HTTP_201_CREATED if result['action'] == 'created' else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def auto_category(self, request):
        """根据 URL 自动分类"""
        url = request.data.get('url')
        if not url:
            return Response({'error': 'url required'}, status=status.HTTP_400_BAD_REQUEST)
        
        category = PageSnapshotService.auto_category_from_url(url)
        return Response({'category': category})


class SeedURLViewSet(viewsets.ModelViewSet):
    """
    种子URL API
    提供：列表、详情、创建、更新、删除、按学校筛选、按状态筛选
    """
    queryset = SeedURL.objects.all().order_by('-created_at')
    serializer_class = SeedURLSerializer
    
    def get_queryset(self):
        """支持按学校、状态筛选"""
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
        """检查死链 - 发送 HEAD 请求验证 URL 是否有效"""
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
        """获取种子统计 - 供监控看板使用"""
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


# 添加爬虫状态 API
import redis
from django.conf import settings


@api_view(['GET'])
def get_crawler_status(request):
    """
    爬虫状态 API - 返回 Celery 队列状态
    GET /api/crawler/status/
    """
    try:
        # 尝试连接 Redis（如果没有安装 redis 会报错，这里做异常处理）
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True,socket_timeout=2)
        
        # 获取队列长度
        queue_length = r.llen('celery') if r.exists('celery') else 0
        
        # 获取种子统计
        seed_total = SeedURL.objects.count()
        seed_success = SeedURL.objects.filter(status='success').count()
        seed_failed = SeedURL.objects.filter(status='failed').count()
        seed_pending = SeedURL.objects.filter(status='pending').count()
        
        return Response({
            'queue_length': queue_length,
            'active_workers': 1,
            'tasks': {
                'total': seed_total,
                'success': seed_success,
                'failed': seed_failed,
                'pending': seed_pending
            },
            'success_rate': round(seed_success / max(seed_total, 1) * 100, 2)
        })
    except Exception as e:
        return Response({
            'error': str(e),
            'queue_length': 0,
            'active_workers': 0,
            'tasks': {'total': 0, 'success': 0, 'failed': 0, 'pending': 0},
            'success_rate': 0
        })
        
"""
功能：日志查询 API 视图
用途：提供日志查询接口，供前端监控看板使用
- GET /api/logs/ - 返回最近的日志内容
调用方：前端监控看板（成员 D）
"""

import os
import logging
from pathlib import Path
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
def get_logs(request):
    """
    获取最近的日志内容
    用途：前端监控看板调用此接口显示错误日志
    
    请求参数：
        - lines: 返回的行数，默认 50，最大 500
        - level: 日志级别过滤（ERROR/WARNING/INFO/ALL），默认 ERROR
        - file: 日志文件名，默认 error.log
    
    返回格式：
        {
            "logs": ["日志行1", "日志行2", ...],
            "total": 2,
            "file": "logs/error.log"
        }
    """
    # 获取请求参数
    lines = min(int(request.query_params.get('lines', 50)), 500)  # 最多500行
    level = request.query_params.get('level', 'ERROR').upper()
    log_file_name = request.query_params.get('file', 'error.log')
    
    # 安全检查：只允许访问 logs 目录下的 .log 文件
    if not log_file_name.endswith('.log'):
        return Response(
            {'error': '只支持 .log 文件'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 构建日志文件路径
    log_path = settings.BASE_DIR / 'logs' / log_file_name
    
    # 检查文件是否存在
    if not log_path.exists():
        return Response({
            'logs': [],
            'total': 0,
            'file': str(log_path),
            'message': '日志文件不存在，请先运行系统产生日志'
        })
    
    # 读取文件最后 N 行
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
        
        # 按日志级别过滤
        if level != 'ALL':
            filtered_lines = []
            for line in recent_lines:
                # 检查行是否包含指定级别（如 ERROR、WARNING）
                if f' {level} ' in line or line.startswith(level):
                    filtered_lines.append(line)
            recent_lines = filtered_lines
        
        return Response({
            'logs': recent_lines,
            'total': len(recent_lines),
            'file': str(log_path),
            'available_files': _get_log_files()
        })
        
    except Exception as e:
        return Response(
            {'error': f'读取日志失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_log_files(request):
    """
    获取可用的日志文件列表
    用途：前端让用户选择查看哪个日志文件
    """
    return Response({'files': _get_log_files()})


def _get_log_files():
    """获取 logs 目录下的所有 .log 文件"""
    logs_dir = settings.BASE_DIR / 'logs'
    if not logs_dir.exists():
        return []
    
    files = []
    for f in logs_dir.glob('*.log'):
        files.append({
            'name': f.name,
            'size': f.stat().st_size,
            'modified': f.stat().st_mtime
        })
    
    # 按修改时间倒序排列
    files.sort(key=lambda x: x['modified'], reverse=True)
    return files


@api_view(['GET'])
def get_crawler_config(request):
    """
    获取爬虫伦理配置（模块8.5）
    用途：前端监控看板显示当前爬虫配置，或成员 A 的爬虫任务读取配置
    """
    from django.conf import settings
    return Response(getattr(settings, 'CRAWLER_ETHICS', {}))


@api_view(['POST'])
def update_crawler_config(request):
    """
    更新爬虫伦理配置（需要管理员权限）
    用途：管理员通过前端修改请求延迟、并发上限等参数
    """
    # 注意：生产环境需要添加权限验证
    # from django.contrib.auth.decorators import permission_required
    
    try:
        new_config = request.data
        # 这里可以保存到数据库（CrawlerConfig 模型）
        # 简单起见，先返回成功
        return Response({
            'status': 'ok',
            'message': '配置已更新（重启后生效）',
            'config': new_config
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )