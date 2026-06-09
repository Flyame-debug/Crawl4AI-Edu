"""
文件名: __init__.py
作用: 提取策略模块入口 —— 统一的数据提取接口
主要功能:
    1. extract_page(): 统一提取入口，自动选择策略（CSS选择器 → 兜底）
    2. 返回标准化的 extracted_data 结构
    3. 集成指纹匹配和策略选择逻辑
"""

import logging
from typing import Dict, Any, Optional

from .fingerprint import compute_fingerprint
from .rules import match_template
from .extractor import extract_by_selectors
from .fallback import fallback_extract

logger = logging.getLogger('apps')


def extract_page(
    raw_html: str,
    markdown: str,
    page_type_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    作用: 统一的数据提取入口，对单个页面执行结构化信息提取

    策略优先级:
        1. 计算 DOM simhash 指纹
        2. 用指纹匹配 Template 表中的提取规则
        3. 命中 → CSS 选择器提取（高置信度）
        4. 未命中 → jieba + 正则兜底提取（中低置信度）

    参数:
        raw_html: 原始 HTML 字符串
        markdown: 模块一转换后的 Markdown 文本
        page_type_hint: 成员A预填的页面类型（teacher/course/research/unknown）

    返回:
        标准 extracted_data 结构：
        {
            'page_type': str,
            'extracted': dict,
            'confidence': float (0~1),
            'method': 'css_selector' / 'fallback' / 'unknown',
        }
    """
    if not raw_html:
        logger.warning('extract_page: raw_html 为空，无法提取')
        return {
            'page_type': 'unknown',
            'extracted': {},
            'confidence': 0.0,
            'method': 'unknown',
        }

    # 步骤1：计算 DOM 指纹
    fingerprint = compute_fingerprint(raw_html)

    # 步骤2：尝试模板匹配
    if fingerprint is not None:
        match_result = match_template(fingerprint)
        if match_result:
            # 步骤3：命中模板 → CSS 选择器提取
            logger.info(
                f'模板匹配成功: {match_result["template_name"]}, '
                f'距离={match_result["distance"]}'
            )
            result = extract_by_selectors(
                raw_html=raw_html,
                rule_selectors=match_result['selectors'],
                page_type=match_result['page_type'],
            )
            result['template_name'] = match_result['template_name']
            return result

    # 步骤4：未命中 → 兜底提取
    logger.info('未匹配到模板，使用兜底提取')
    result = fallback_extract(markdown, page_type_hint)
    return result
