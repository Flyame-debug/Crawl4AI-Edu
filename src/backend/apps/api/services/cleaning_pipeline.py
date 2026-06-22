"""
文件名: cleaning_pipeline.py
作用: 模块5核心 —— 清洗流水线主函数，串联AI清洗→规则校验→降级兜底
主要功能:
    1. 读取 PageSnapshot（markdown + user_prompt）
    2. 调用 AI 智能清洗提取（模块3）
    3. 对 AI 结果做规则校验（模块4）
    4. AI 失败时判断重试次数，最后一次重试降级到纯规则兜底提取（模块4）
    5. 返回统一结果结构，由调用方决定是否写库
调用方: tasks.py / 手动调试
"""

import logging
from typing import Dict, Any

from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger('apps.api.services.cleaning_pipeline')


class RetryNeededException(Exception):
    """
    作用: 流水线发出的重试信号异常，由 tasks.py 捕获并触发 Celery 重试
    """
    pass


def run_cleaning_pipeline(
    page_snapshot_id: int,
    retry_count: int = 0,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    作用: 单条页面清洗流水线主函数，串联 AI 清洗 → 规则校验 → 降级兜底

    流程:
        1. 读取 PageSnapshot（markdown + user_prompt + page_type）
        2. 调用 ai_clean_and_extract() 进行 AI 清洗提取
        3. AI 成功 → 调用 validate_with_rules() 做规则校验修正
        4. AI 失败 → 判断重试次数:
           - 未到最后一次重试: 返回 action='retry'，由调用方触发 Celery 重试
           - 已到最后一次重试: 降级调用 extract_by_rules_fallback() 纯规则提取
        5. 返回统一结果结构

    参数:
        page_snapshot_id: 页面快照 ID
        retry_count: 当前重试次数（0表示首次，由 Celery self.request.retries 传入）
        max_retries: 最大重试次数（对应 Celery 任务的 max_retries）

    返回:
        {
            'action': 'completed' | 'retry' | 'error',
            'extracted_data': {...} 或 None,
            'error': '错误信息' 或 None
        }

        action 说明:
        - 'completed': 处理完成（AI成功或规则兜底完成），调用方可写入 ai_cleaned
        - 'retry': AI 暂时失败需重试，调用方应触发 Celery 重试
        - 'error': 硬错误（如 markdown 为空），调用方应写入 error 状态且不重试
    """
    from apps.api.models import PageSnapshot
    from apps.api.services.ai_cleaner import ai_clean_and_extract
    from apps.api.services.rule_validator import (
        validate_with_rules,
        extract_by_rules_fallback,
    )

    # ============================================================
    # 第0步：读取 PageSnapshot
    # ============================================================
    try:
        page = PageSnapshot.objects.get(id=page_snapshot_id)
    except ObjectDoesNotExist:
        logger.error(f"页面快照不存在: id={page_snapshot_id}")
        return {
            'action': 'error',
            'extracted_data': None,
            'error': f'页面快照不存在: id={page_snapshot_id}',
        }

    markdown = page.markdown
    user_prompt = page.user_prompt
    page_type_hint = page.page_type

    logger.info(
        f"流水线启动: page_id={page_snapshot_id}, retry={retry_count}/{max_retries}, "
        f"url={page.url}, page_type_hint={page_type_hint}"
    )

    # ============================================================
    # 第0步校验：markdown 为空 → 硬错误，不重试
    # ============================================================
    if not markdown or not markdown.strip():
        logger.warning(f"markdown 为空: page_id={page_snapshot_id}")
        return {
            'action': 'error',
            'extracted_data': None,
            'error': '输入Markdown内容为空，无法进行清洗',
        }

    # ============================================================
    # 第1步：调用 AI 清洗提取（模块3）
    # ============================================================
    logger.debug(f"调用AI清洗: page_id={page_snapshot_id}, markdown长度={len(markdown)}")
    ai_result = ai_clean_and_extract(
        markdown=markdown,
        user_prompt=user_prompt,
        page_type_hint=page_type_hint,
    )

    # AI 调用失败 → 判断是否需要重试还是降级
    if not ai_result['success']:
        ai_error = ai_result.get('error', 'AI清洗未知错误')
        logger.warning(
            f"AI清洗失败: page_id={page_snapshot_id}, "
            f"retry={retry_count}/{max_retries}, error={ai_error}"
        )

        # 检查是否还有重试机会
        if retry_count < max_retries - 1:
            # 未到最后一次重试 → 返回 retry，由调用方触发 Celery 重试
            return {
                'action': 'retry',
                'extracted_data': None,
                'error': f'AI清洗失败（第{retry_count + 1}次尝试），将在Celery重试: {ai_error}',
            }
        else:
            # 已达最大重试次数 → 降级到纯规则兜底提取
            logger.info(
                f"AI清洗已重试{max_retries}次均失败，降级到纯规则兜底提取: "
                f"page_id={page_snapshot_id}"
            )
            fallback_result = _run_fallback_extraction(
                markdown, page_type_hint, page_snapshot_id
            )
            return {
                'action': 'completed',
                'extracted_data': fallback_result,
                'error': None,
            }

    # ============================================================
    # 第2步：AI 成功 → 规则校验修正（模块4）
    # ============================================================
    ai_data = ai_result['data']
    logger.debug(f"AI清洗成功，进入规则校验: page_id={page_snapshot_id}")

    try:
        validated_result = validate_with_rules(
            ai_result=ai_data,
            markdown=markdown,
        )
        logger.info(
            f"规则校验完成: page_id={page_snapshot_id}, "
            f"method={validated_result.get('method')}, "
            f"passed={validated_result.get('_validation', {}).get('passed')}"
        )
    except Exception as e:
        # 规则校验异常 → 保留AI原始结果，记录warning继续
        logger.error(
            f"规则校验异常，保留AI原始结果: page_id={page_snapshot_id}, error={str(e)}"
        )
        validated_result = ai_data.copy()
        validated_result['_validation'] = {
            'passed': False,
            'fixes': [],
            'warnings': [{'message': f'规则校验异常，保留AI原始结果: {str(e)}'}],
        }

    # ============================================================
    # 第3步：返回成功结果
    # ============================================================
    logger.info(
        f"流水线完成: page_id={page_snapshot_id}, "
        f"method={validated_result.get('method')}, "
        f"confidence={validated_result.get('confidence')}"
    )

    return {
        'action': 'completed',
        'extracted_data': validated_result,
        'error': None,
    }


def _run_fallback_extraction(
    markdown: str,
    page_type_hint: str = None,
    page_snapshot_id: int = None
) -> Dict[str, Any]:
    """
    作用: 执行纯规则兜底提取，并处理可能的异常

    参数:
        markdown: 原始 Markdown 文本
        page_type_hint: 页面类型提示
        page_snapshot_id: 页面快照 ID（仅用于日志）

    返回:
        兜底提取结果字典，结构与模块3输出一致:
        {page_type, content (Markdown), method: 'rule_fallback', confidence}
    """
    from apps.api.services.rule_validator import extract_by_rules_fallback

    try:
        fallback_result = extract_by_rules_fallback(
            markdown=markdown,
            page_type_hint=page_type_hint,
        )
        logger.info(
            f"纯规则兜底提取完成: page_id={page_snapshot_id}, "
            f"page_type={fallback_result.get('page_type')}, "
            f"confidence={fallback_result.get('confidence')}"
        )
        return fallback_result

    except Exception as e:
        # 兜底也失败了 → 返回 extraction_error
        logger.error(
            f"纯规则兜底提取也失败: page_id={page_snapshot_id}, error={str(e)}"
        )
        return {
            'page_type': page_type_hint or 'unknown',
            'content': '未能从页面中提取到有效信息。',
            'method': 'extraction_error',
            'confidence': 'low',
        }
