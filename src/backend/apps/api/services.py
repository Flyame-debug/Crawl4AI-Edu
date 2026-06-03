"""
功能：业务逻辑服务层
用途：封装核心业务逻辑，供 API 视图和 Celery 任务调用
- 增量更新逻辑：对比 content_hash，相同跳过
- 版本控制：内容变化时创建新版本
调用方：views.py 和成员 A 的 Celery 任务
"""

import hashlib
from django.utils import timezone
from .models import PageSnapshot


class PageSnapshotService:
    """网页快照服务 - 处理增量更新和版本控制"""
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """计算内容的 SHA256 哈希值"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def save_or_update(url: str, markdown: str, category: str = None) -> dict:
        """
        增量保存网页内容
        - 如果内容无变化，跳过
        - 如果内容有变化，创建新版本记录
        
        返回: {'action': 'created'/'skipped'/'updated', 'obj': PageSnapshot}
        """
        content_hash = PageSnapshotService.compute_hash(markdown)
        
        # 查找最新版本的快照
        latest = PageSnapshot.objects.filter(url=url).order_by('-version').first()
        
        # 如果存在且哈希相同，跳过
        if latest and latest.content_hash == content_hash:
            return {'action': 'skipped', 'obj': latest}
        
        # 计算新版本号
        new_version = (latest.version + 1) if latest else 1
        
        # 创建新版本
        snapshot = PageSnapshot.objects.create(
            url=url,
            markdown=markdown,
            content_hash=content_hash,
            category=category,
            version=new_version
        )
        
        return {'action': 'created' if new_version == 1 else 'updated', 'obj': snapshot}
    
    @staticmethod
    def auto_category_from_url(url: str) -> str:
        """根据 URL 自动判断分类"""
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in ['/teacher/', '/faculty/', '/professor/']):
            return '师资'
        elif any(keyword in url_lower for keyword in ['/course/', '/syllabus/', '/curriculum/']):
            return '课程'
        elif any(keyword in url_lower for keyword in ['/research/', '/paper/', '/publication/']):
            return '科研'
        else:
            return '其他'