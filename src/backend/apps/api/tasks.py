"""
文件名: tasks.py
作用: Celery 异步任务定义，供成员C配置 Beat 定时调度
主要功能:
    1. process_conversion_task: 定时批量处理 HTML→Markdown 转换
    2. 支持指数退避重试（60s、120s、240s）
"""

import logging
from celery import shared_task
from apps.api.management.commands.process_conversion import Command

logger = logging.getLogger('apps')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_conversion_task(self):
    """
    作用: Celery 定时任务 —— 批量处理 HTML→Markdown 转换
    
    每5分钟由 Celery Beat 调度执行，每次处理最多50条待转换页面。
    使用指数退避重试策略：第1次重试延迟60秒，第2次120秒，第3次240秒。
    """
    try:
        logger.info('Celery 定时任务启动: process_conversion_task')
        cmd = Command()
        cmd.handle(batch_size=50)
        logger.info('Celery 定时任务完成: process_conversion_task')
    except Exception as exc:
        logger.error(f'process_conversion_task 执行异常: {exc}')
        # 指数退避重试
        countdown = 60 * (2 ** self.request.retries)
        logger.info(f'将在 {countdown} 秒后进行第 {self.request.retries + 1} 次重试')
        raise self.retry(exc=exc, countdown=countdown)
