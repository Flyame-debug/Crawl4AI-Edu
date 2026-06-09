"""
文件名: rules.py
作用: 提取规则加载与模板匹配
主要功能:
    1. 从 Template 模型（config.extraction_rules）加载提取规则
    2. 根据页面指纹匹配最相似的模板规则
    3. 提供默认规则配置的创建工具
"""

import logging
from typing import Optional, Dict, Any

from .fingerprint import hamming_distance

logger = logging.getLogger('apps')

# 默认的海明距离匹配阈值
DEFAULT_HAMMING_THRESHOLD = 10


def match_template(page_fingerprint: int) -> Optional[Dict[str, Any]]:
    """
    作用: 根据页面 simhash 指纹匹配最佳模板提取规则

    遍历 Template 表中所有配置了 extraction_rules 的记录，
    计算指纹海明距离，返回最匹配的规则配置。

    参数:
        page_fingerprint: 当前页面的 simhash 指纹值

    返回:
        匹配成功时返回 {
            'template_name': str,
            'page_type': str,
            'selectors': dict,
            'distance': int,
        }
        匹配失败时返回 None
    """
    from apps.api.models import Template

    if page_fingerprint is None:
        return None

    templates = Template.objects.filter(
        config__has_key='extraction_rules'
    )

    best_match = None
    best_distance = float('inf')

    for template in templates:
        try:
            rules = template.config.get('extraction_rules', {})
            if not rules:
                continue

            template_fp = rules.get('fingerprint')
            if template_fp is None:
                continue

            distance = hamming_distance(template_fp, page_fingerprint)

            if distance < best_distance:
                best_distance = distance
                best_match = {
                    'template_name': template.name,
                    'page_type': rules.get('page_type', 'unknown'),
                    'selectors': rules.get('selectors', {}),
                    'distance': distance,
                }
        except Exception as e:
            logger.warning(f'遍历模板 {template.name} 时出错: {e}')
            continue

    if best_match is None:
        return None

    # 检查是否在阈值内
    if best_match['distance'] <= DEFAULT_HAMMING_THRESHOLD:
        logger.info(
            f'模板匹配成功: {best_match["template_name"]}, '
            f'距离={best_match["distance"]}, page_type={best_match["page_type"]}'
        )
        return best_match

    logger.info(
        f'无模板匹配（最小距离={best_match["distance"]} > 阈值={DEFAULT_HAMMING_THRESHOLD}）'
    )
    return None


def get_rule_by_page_type(page_type: str) -> Optional[Dict[str, Any]]:
    """
    作用: 按 page_type 查找任意一个匹配的模板规则（用于兜底匹配时参考）

    参数:
        page_type: 页面类型，如 teacher/course/research

    返回:
        匹配的规则配置字典，失败返回 None
    """
    from apps.api.models import Template

    templates = Template.objects.filter(
        config__extraction_rules__page_type=page_type
    )

    for template in templates:
        rules = template.config.get('extraction_rules', {})
        if rules:
            return {
                'template_name': template.name,
                'page_type': rules.get('page_type', page_type),
                'selectors': rules.get('selectors', {}),
                'distance': 0,
            }

    return None


def get_default_rules_config(page_type: str) -> Dict[str, Any]:
    """
    作用: 返回各页面类型的默认提取规则配置

    在初始化模板记录时使用，基于常见中文高校网站布局编写通用选择器。
    """
    rules_map = {
        'teacher': {
            'fingerprint': 0,  # 占位，实际使用时需替换
            'page_type': 'teacher',
            'selectors': {
                'name': 'h1, .name, .teacher-name, .faculty-name, [itemprop="name"], .profile-name',
                'title': '.title, .position, .job-title, .rank',
                'department': '.department, .college, .faculty, .school, .org',
                'research': '.research, .interests, .research-area, .research-interest, .field',
                'email': 'a[href^="mailto:"], .email, .contact-email',
                'phone': '.phone, .tel, .contact-phone, .telephone',
                'office': '.office, .location, .address, .room, .workplace',
            },
        },
        'course': {
            'fingerprint': 0,
            'page_type': 'course',
            'selectors': {
                'course_name': 'h1, .course-name, .course-title, .name',
                'teacher': '.teacher, .instructor, .lecturer, .professor',
                'credits': '.credits, .credit, .credit-hours',
                'hours': '.hours, .class-hours, .total-hours, .duration',
                'syllabus': '.syllabus, .description, .intro, .overview, .content',
                'semester': '.semester, .term, .academic-year',
            },
        },
        'research': {
            'fingerprint': 0,
            'page_type': 'research',
            'selectors': {
                'paper_title': 'h1, .paper-title, .article-title, .title',
                'authors': '.authors, .author-list, .contributors, .writer',
                'journal': '.journal, .publication, .publisher, .venue',
                'year': '.year, .pub-year, .date, .publication-date',
                'doi': '.doi, .paper-doi, a[href*="doi.org"]',
            },
        },
    }

    return rules_map.get(page_type, {
        'fingerprint': 0,
        'page_type': 'unknown',
        'selectors': {},
    })
