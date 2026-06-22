"""
文件名: tasks.py
作用: Celery 异步任务定义，供成员C配置 Beat 定时调度 - V2.0
主要功能:
    1. process_conversion_task: 定时批量处理 HTML→Markdown 转换
    2. process_ai_cleaning_task: V2.0新增 - 批量AI清洗任务（成员B）
    3. monitor_ollama_health: V2.0新增 - Ollama 服务健康监控（成员B）
    4. clean_preview_tasks: V2.0新增 - 清理过期预览数据
    5. sync_running_tasks_status: V2.0新增 - 同步运行中任务状态
    6. generate_rules_task: V2.0新增 - 异步生成采集规则（成员A）
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger('apps')


# ==================== 原有任务 ====================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_conversion_task(self):
    """
    作用: Celery 定时任务 —— 批量处理 HTML→Markdown 转换
    
    每5分钟由 Celery Beat 调度执行，每次处理最多50条待转换页面。
    使用指数退避重试策略：第1次重试延迟60秒，第2次120秒，第3次240秒。
    """
    try:
        logger.info('Celery 定时任务启动: process_conversion_task')
        from apps.api.management.commands.process_conversion import Command
        cmd = Command()
        cmd.handle(batch_size=50)
        logger.info('Celery 定时任务完成: process_conversion_task')
    except Exception as exc:
        logger.error(f'process_conversion_task 执行异常: {exc}')
        countdown = 60 * (2 ** self.request.retries)
        logger.info(f'将在 {countdown} 秒后进行第 {self.request.retries + 1} 次重试')
        raise self.retry(exc=exc, countdown=countdown)


# ==================== V2.0 新增任务 ====================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_ai_cleaning_task(self, batch_size: int = 20):
    """
    V2.0新增：批量AI清洗任务（成员B使用）
    
    功能：
        1. 获取 process_status='raw_converted' 的页面
        2. 调用清洗流水线（AI清洗 → 规则校验 → 降级兜底）
        3. 更新页面状态为 ai_cleaned 或 error
        4. AI暂时失败时通过Celery重试（指数退避），重试耗尽后降级到规则兜底
    
    参数:
        batch_size: 每次处理的最大数量（默认20）
    """
    try:
        logger.info(f'Celery AI清洗任务启动: batch_size={batch_size}')
        
        from apps.api.models import PageSnapshot
        from apps.api.services.cleaning_pipeline import (
            run_cleaning_pipeline,
            RetryNeededException,
        )
        from apps.api.services.snapshot_service import PageSnapshotService
        
        # 获取待清洗页面
        pending_pages = PageSnapshot.objects.filter(
            process_status='raw_converted'
        ).exclude(
            Q(markdown__isnull=True) | Q(markdown='')
        )[:batch_size]
        
        if not pending_pages:
            logger.info('没有待清洗的页面')
            return {'processed': 0, 'success': 0, 'failed': 0}
        
        success_count = 0
        failed_count = 0
        
        for page in pending_pages:
            try:
                # 状态前置检查：防止其他进程并发处理同一页面
                if page.process_status == 'ai_cleaned':
                    continue

                # 调用清洗流水线（传入当前重试次数，用于判断是否需要降级）
                result = run_cleaning_pipeline(
                    page_snapshot_id=page.id,
                    retry_count=self.request.retries,
                    max_retries=self.max_retries,
                )

                if result['action'] == 'completed':
                    # AI成功（含规则校验修正）或降级兜底成功 → 写入 ai_cleaned
                    extracted_data = result['extracted_data']
                    PageSnapshotService.update_clean_result(
                        snapshot_id=page.id,
                        extracted_data=extracted_data,
                        process_status='ai_cleaned',
                    )
                    success_count += 1
                    logger.info(
                        f'流水线完成: {page.url}, '
                        f'method={extracted_data.get("method")}, '
                        f'confidence={extracted_data.get("confidence")}'
                    )

                elif result['action'] == 'retry':
                    # AI暂时失败，需Celery重试 → 保持页面状态为 raw_converted，抛重试信号
                    logger.warning(
                        f'流水线请求重试: {page.url}, '
                        f'retry={self.request.retries + 1}/{self.max_retries}, '
                        f'error={result["error"]}'
                    )
                    raise RetryNeededException(result['error'])

                else:  # 'error'：硬错误，不重试
                    PageSnapshotService.update_clean_result(
                        snapshot_id=page.id,
                        extracted_data={},
                        process_status='error',
                        error_info=result['error'][:500],
                    )
                    failed_count += 1
                    logger.warning(
                        f'流水线硬错误: {page.url}, error={result["error"]}'
                    )

            except RetryNeededException:
                # 重试信号 → 传播到外层，触发 Celery 重试
                raise
            except Exception as e:
                logger.error(f'流水线异常: {page.url}, error={str(e)}')
                PageSnapshotService.update_clean_result(
                    snapshot_id=page.id,
                    extracted_data={},
                    process_status='error',
                    error_info=str(e)[:500],
                )
                failed_count += 1

        logger.info(
            f'AI清洗任务完成: 处理{len(pending_pages)}条, '
            f'成功{success_count}, 失败{failed_count}'
        )

        return {
            'processed': len(pending_pages),
            'success': success_count,
            'failed': failed_count,
        }

    except RetryNeededException as exc:
        # 流水线发出的重试信号 → 触发 Celery 指数退避重试
        countdown = 60 * (2 ** self.request.retries)
        logger.info(
            f'触发Celery重试: retry={self.request.retries + 1}/{self.max_retries}, '
            f'countdown={countdown}s, reason={exc}'
        )
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.error(f'process_ai_cleaning_task 执行异常: {exc}')
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task
def clean_preview_tasks():
    """
    V2.0新增：清理过期的预览任务数据
    
    功能：
        删除创建时间超过7天的预览任务数据
        释放存储空间
    
    建议调度：每天凌晨2点执行一次
    """
    try:
        logger.info('开始清理过期预览任务数据')
        
        from apps.api.models import PageSnapshot, CrawlTask
        
        expiry_date = timezone.now() - timedelta(days=7)
        
        # 清理预览页面
        pages_deleted, _ = PageSnapshot.objects.filter(
            task_type='preview',
            created_at__lt=expiry_date
        ).delete()
        
        # 清理预览任务
        tasks_deleted, _ = CrawlTask.objects.filter(
            task_type='preview',
            status__in=['completed', 'stopped', 'failed'],
            created_at__lt=expiry_date
        ).delete()
        
        logger.info(f'清理完成: 删除{pages_deleted}个预览页面, {tasks_deleted}个预览任务')
        
        return {
            'pages_deleted': pages_deleted,
            'tasks_deleted': tasks_deleted
        }
        
    except Exception as e:
        logger.error(f'清理预览任务失败: {str(e)}')
        return {'error': str(e)}


@shared_task
def sync_running_tasks_status():
    """
    V2.0新增：同步运行中任务的状态
    
    功能：
        检查长时间未更新的running任务，标记为failed
        防止僵尸任务占用队列
    
    建议调度：每10分钟执行一次
    """
    try:
        from apps.api.models import CrawlTask
        
        timeout_minutes = 30  # 30分钟无更新视为超时
        timeout_time = timezone.now() - timedelta(minutes=timeout_minutes)
        
        # 查找超时的运行中任务
        stuck_tasks = CrawlTask.objects.filter(
            status='running',
            updated_at__lt=timeout_time
        )
        
        count = stuck_tasks.count()
        if count > 0:
            stuck_tasks.update(
                status='failed',
                error_message=f'任务超时：超过{timeout_minutes}分钟无更新'
            )
            logger.warning(f'标记 {count} 个超时任务为失败')
        
        return {'stuck_tasks_marked': count}
        
    except Exception as e:
        logger.error(f'同步任务状态失败: {str(e)}')
        return {'error': str(e)}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_rules_task(self, user_prompt: str, html_skeleton: str, 
                        ai_model: str = 'qwen2:7b', 
                        ai_api_url: str = 'http://127.0.0.1:11434'):
    """
    V2.0新增：异步生成采集规则（成员A使用）
    
    参数:
        user_prompt: 用户提取指令
        html_skeleton: HTML骨架
        ai_model: AI模型名称
        ai_api_url: AI服务地址
    
    返回:
        {'rule_content': str, 'status': str, 'error_msg': str}
    """
    try:
        logger.info(f'异步生成采集规则: model={ai_model}')
        
        from apps.api.services.ai_service import get_ollama_service
        
        ollama = get_ollama_service(api_url=ai_api_url, model=ai_model)
        result = ollama.generate_rules(user_prompt, html_skeleton)
        
        logger.info(f'规则生成完成: status={result["status"]}')
        return result
        
    except Exception as exc:
        logger.error(f'generate_rules_task 执行异常: {exc}')
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=1)
def monitor_ollama_health(self):
    """
    V2.0新增：Ollama 服务健康监控（成员B）
    
    功能：
        1. 检测 Ollama API 可达性
        2. 检测模型是否就绪
        3. 健康时静默（debug日志），异常时记录 error 日志
    
    建议调度：每5分钟执行一次
    
    返回:
        {'healthy': bool, 'api_url': str, 'model': str, ...}
    """
    try:
        from apps.api.services.ai_service import get_ollama_service

        ollama = get_ollama_service()
        result = ollama.check_health()

        if result['healthy']:
            logger.debug(
                f'Ollama 健康检查通过: {ollama.api_url}, '
                f'模型: {ollama.model}'
            )
            return {
                'healthy': True,
                'api_url': ollama.api_url,
                'model': ollama.model,
            }
        else:
            logger.error(
                f'Ollama 健康检查异常: '
                f'api_reachable={result["api_reachable"]}, '
                f'model_ready={result["model_ready"]}, '
                f'error={result.get("error")}'
            )
            return {
                'healthy': False,
                'detail': result.get('error', '未知异常'),
            }

    except Exception as e:
        logger.error(f'Ollama 健康监控任务执行异常: {str(e)}')
        return {'healthy': False, 'error': str(e)}


@shared_task
def batch_convert_html_to_markdown(batch_size: int = 50):
    """
    V2.0新增：批量转换HTML到Markdown
    
    与原有 process_conversion_task 功能相同，提供更灵活的批量控制
    """
    try:
        logger.info(f'批量HTML转Markdown启动: batch_size={batch_size}')
        
        from apps.api.management.commands.process_conversion import Command
        cmd = Command()
        cmd.handle(batch_size=batch_size)
        
        logger.info('批量HTML转Markdown完成')
        return {'batch_size': batch_size, 'status': 'completed'}
        
    except Exception as e:
        logger.error(f'批量转换失败: {str(e)}')
        return {'error': str(e)}