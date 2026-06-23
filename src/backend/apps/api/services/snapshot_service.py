"""
文件名: snapshot_service.py
作用: 网页快照业务逻辑服务，处理增量更新和版本控制 - V2.0
主要功能:
    1. 计算内容 SHA256 哈希值
    2. 增量保存网页内容（对比哈希，相同跳过）
    3. 内容变化时创建新版本记录
    4. 根据 URL 自动判断分类（teacher/course/research/other）
    5. V2.0新增：支持任务类型、任务关联、处理状态管理
调用方: views.py 和成员 A 的 Celery 任务
"""

import hashlib
import logging
from django.utils import timezone
from django.db import transaction
from apps.api.models import PageSnapshot, CrawlTask

logger = logging.getLogger(__name__)


class PageSnapshotService:
    """网页快照服务 - 处理增量更新和版本控制 V2.0"""
    
    # URL分类关键词映射
    CATEGORY_KEYWORDS = {
        'teacher': ['/teacher/', '/faculty/', '/professor/', '/staff/', '/people/', '/jiaoshi/'],
        'course': ['/course/', '/syllabus/', '/curriculum/', '/kecheng/', '/class/'],
        'research': ['/research/', '/paper/', '/publication/', '/yanjiu/', '/lunwen/'],
        'news': ['/news/', '/notice/', '/gonggao/', '/xinwen/'],
    }
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """计算内容的 SHA256 哈希值"""
        if not content:
            return hashlib.sha256("".encode('utf-8')).hexdigest()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def auto_category_from_url(url: str) -> str:
        """
        根据 URL 自动判断分类（V2.0使用英文key）
        返回值: 'teacher', 'course', 'research', 'news', 'other'
        """
        url_lower = url.lower()
        
        for category, keywords in PageSnapshotService.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in url_lower:
                    return category
        
        return 'other'
    
    @staticmethod
    def save_or_update(
        url: str, 
        markdown: str, 
        category: str = None,
        raw_html: str = None,
        task: CrawlTask = None,
        task_type: str = 'formal',
        user_prompt: str = None,
        images: list = None
    ) -> dict:
        """增量保存网页内容 - V2.0"""
        if not markdown:
            markdown = ""
    
        content_hash = PageSnapshotService.compute_hash(markdown)
    
        filter_kwargs = {'url': url}
        if task:
            filter_kwargs['task_id'] = task.task_id
    
        existing = PageSnapshot.objects.filter(**filter_kwargs).first()
    
        if existing and existing.content_hash == content_hash:
            logger.debug(f"内容无变化，跳过保存: {url}")
            return {'action': 'skipped', 'obj': existing}
    
        if not category:
            category = PageSnapshotService.auto_category_from_url(url)
    
    # ✅ 去掉预览任务限制（注释掉或删除）
    # if task_type == 'preview':
    #     preview_count = PageSnapshot.objects.filter(task_type='preview').count()
    #     if preview_count >= 10:
    #         logger.warning(f"预览任务已达上限10条，跳过保存: {url}")
    #         return {'action': 'skipped', 'obj': None}
    
        data = {
            'url': url,
            'markdown': markdown,
            'content_hash': content_hash,
            'category': category,
            'task_type': task_type,
            'user_prompt': user_prompt,
            'process_status': 'raw_converted',
            'processed_at': timezone.now(),
        }
    
        if raw_html:
            data['raw_html'] = raw_html
        if task:
            data['task_id'] = task.task_id
        if images:
            data['images'] = images
    
        if existing:
            data['version'] = existing.version + 1
            for key, value in data.items():
                setattr(existing, key, value)
            existing.save()
            action = 'updated'
            obj = existing
        else:
            data['version'] = 1
            obj = PageSnapshot.objects.create(**data)
            action = 'created'
    
        logger.info(f"{action} 页面快照: {url}, 版本: {obj.version}, 任务类型: {task_type}")
    
        return {'action': action, 'obj': obj}
    
    @staticmethod
    def update_clean_result(
        snapshot_id: int, 
        extracted_data: dict, 
        process_status: str, 
        error_info: str = None
    ) -> bool:
        """
        V2.0新增：更新AI清洗结果
        
        参数:
            snapshot_id: 快照ID
            extracted_data: 结构化提取的数据
            process_status: 处理状态（ai_cleaned/error）
            error_info: 错误信息（可选）
        
        返回: 是否更新成功
        """
        try:
            snapshot = PageSnapshot.objects.get(id=snapshot_id)
            snapshot.extracted_data = extracted_data or {}
            snapshot.process_status = process_status
            if error_info:
                snapshot.error_info = error_info
            snapshot.processed_at = timezone.now()
            snapshot.save()
            
            logger.info(f"更新清洗结果: snapshot_id={snapshot_id}, status={process_status}")
            return True
            
        except PageSnapshot.DoesNotExist:
            logger.error(f"快照不存在: snapshot_id={snapshot_id}")
            return False
        except Exception as e:
            logger.error(f"更新清洗结果失败: {str(e)}")
            return False
    
    @staticmethod
    def get_pending_for_cleaning(limit: int = 10) -> list:
        """
        V2.0新增：获取待清洗的页面（供成员B轮询）
        
        返回: process_status='raw_converted' 的页面列表
        """
        return list(
            PageSnapshot.objects.filter(process_status='raw_converted')
            .order_by('created_at')[:limit]
        )
    
    @staticmethod
    def get_by_task(task_id: str) -> list:
        """
        V2.0新增：获取任务关联的所有页面
        """
        return list(
            PageSnapshot.objects.filter(task__task_id=task_id)
            .order_by('created_at')
        )
    
    @staticmethod
    def clean_preview_tasks() -> int:
        """
        V2.0新增：清理过期的预览任务数据
        预览任务数据保留7天后自动清理
        """
        from datetime import timedelta
        
        expiry_date = timezone.now() - timedelta(days=7)
        deleted_count, _ = PageSnapshot.objects.filter(
            task_type='preview',
            created_at__lt=expiry_date
        ).delete()
        
        if deleted_count:
            logger.info(f"清理过期预览任务数据: {deleted_count} 条")
        
        return deleted_count
    
    @staticmethod
    def get_statistics() -> dict:
        """
        V2.0新增：获取页面统计信息
        """
        total = PageSnapshot.objects.count()
        
        return {
            'total': total,
            'by_process_status': {
                'pending': PageSnapshot.objects.filter(process_status='pending').count(),
                'raw_converted': PageSnapshot.objects.filter(process_status='raw_converted').count(),
                'ai_cleaned': PageSnapshot.objects.filter(process_status='ai_cleaned').count(),
                'error': PageSnapshot.objects.filter(process_status='error').count(),
            },
            'by_task_type': {
                'preview': PageSnapshot.objects.filter(task_type='preview').count(),
                'formal': PageSnapshot.objects.filter(task_type='formal').count(),
            },
            'by_category': dict(
                PageSnapshot.objects.values('category')
                .annotate(count=models.Count('id'))
                .values_list('category', 'count')
            ),
            'extracted_rate': round(
                PageSnapshot.objects.filter(
                    extracted_data__isnull=False
                ).exclude(extracted_data={}).count() / max(total, 1) * 100, 2
            ),
        }


# 需要导入models以支持Count
from django.db import models