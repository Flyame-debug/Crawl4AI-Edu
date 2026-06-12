"""
文件名: extractor.py
作用: CSS 选择器提取引擎 —— 根据模板规则从 HTML 中提取结构化字段
主要功能:
    1. 使用 lxml + cssselect 根据 CSS 选择器规则逐字段提取
    2. 计算提取置信度评分
    3. 返回标准化的 extracted_data 结构
"""

import logging
import re
from typing import Dict, Any, Optional, List

from lxml import html

logger = logging.getLogger('apps')


def extract_by_selectors(
    raw_html: str,
    rule_selectors: Dict[str, str],
    page_type: str = 'unknown',
) -> Dict[str, Any]:
    """
    作用: 根据 CSS 选择器规则从原始 HTML 中提取结构化数据

    处理流程:
        1. lxml 解析 HTML
        2. 逐字段应用 CSS 选择器，取第一个匹配的文本
        3. 对提取结果做清洗（去除多余空白、HTML 标签等）
        4. 计算置信度评分

    参数:
        raw_html: 原始 HTML 字符串
        rule_selectors: 字段名 → CSS 选择器的映射字典
        page_type: 页面类型标识

    返回:
        标准 extracted_data 结构:
        {
            'page_type': str,
            'extracted': dict,
            'confidence': float,
            'method': str,
        }
    """
    if not raw_html or not rule_selectors:
        return {
            'page_type': page_type,
            'extracted': {},
            'confidence': 0.0,
            'method': 'css_selector',
        }

    try:
        tree = html.fromstring(raw_html)
    except Exception as e:
        logger.error(f'lxml 解析 HTML 失败: {e}')
        return {
            'page_type': page_type,
            'extracted': {},
            'confidence': 0.0,
            'method': 'css_selector',
        }

    extracted = {}
    field_count = 0
    filled_count = 0

    # 特殊处理：邮箱字段同时搜索 mailto 链接和文本
    email_value = None

    for field_name, selector in rule_selectors.items():
        field_count += 1
        try:
            elements = tree.cssselect(selector)
            if elements:
                # 对于邮箱字段，优先匹配 href 属性中的 mailto 地址
                if field_name == 'email':
                    email_value = _extract_email_from_elements(elements)
                    if email_value:
                        extracted[field_name] = email_value
                        filled_count += 1
                        continue

                # 常规字段：取第一个非空文本
                value = _extract_text_from_elements(elements)
                if value:
                    # 针对特定字段的智能清洗
                    value = _clean_field_value(field_name, value)
                    extracted[field_name] = value
                    filled_count += 1
                else:
                    extracted[field_name] = ''
            else:
                extracted[field_name] = ''
        except Exception as e:
            logger.debug(f'选择器提取字段 "{field_name}" 异常: {e}')
            extracted[field_name] = ''

    # 计算置信度：已填充字段数 / 总字段数
    confidence = round(filled_count / max(field_count, 1), 2)

    logger.info(
        f'CSS 选择器提取完成: page_type={page_type}, '
        f'置信度={confidence}, 已填充 {filled_count}/{field_count} 字段'
    )

    return {
        'page_type': page_type,
        'extracted': extracted,
        'confidence': confidence,
        'method': 'css_selector',
    }


def _extract_text_from_elements(elements: List) -> Optional[str]:
    """
    作用: 从 lxml 元素列表中提取第一个非空文本内容
    """
    for el in elements:
        # 优先取 text_content（包含所有文本节点）
        text = el.text_content() if hasattr(el, 'text_content') else ''
        text = text.strip()
        if text:
            return _clean_text(text)
    return None


def _extract_email_from_elements(elements: List) -> Optional[str]:
    """
    作用: 从 lxml 元素列表中提取邮箱地址

    优先从 <a href="mailto:xxx"> 中提取，其次在文本中用正则匹配。
    """
    for el in elements:
        # 检查 href 属性中的 mailto
        href = el.get('href', '')
        if href and href.startswith('mailto:'):
            email = href.replace('mailto:', '').strip()
            email = email.split('?')[0]  # 去除查询参数
            if _is_valid_email(email):
                return email

        # 在文本内容中用正则匹配邮箱
        text = el.text_content() if hasattr(el, 'text_content') else ''
        match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if match:
            return match.group(0).strip()

    return None


def _clean_field_value(field_name: str, value: str) -> str:
    """
    作用: 针对特定字段名做智能清洗

    - 姓名：去除"姓名："等前缀
    - 职称：取第一个匹配项
    - 研究方向：去除"研究方向："前缀
    - 电话：只保留第一个匹配的电话号码
    """
    if field_name == 'name':
        # 去除可能的"姓 名："前缀
        value = re.sub(r'^(姓\s*名[：:]|姓名[：:]|名字[：:])', '', value).strip()
        # 限制长度（姓名通常不超过20字）
        if len(value) > 20:
            value = value[:20]

    elif field_name == 'title':
        # 只保留第一个职称
        titles = re.findall(
            r'(教授|副教授|讲师|助教|研究员|副研究员|工程师|高级工程师|'
            r'院士|博士|硕士|导师|博士生导师|硕士生导师|院长|副院长|'
            r'系主任|学科带头人)',
            value,
        )
        if titles:
            value = titles[0]

    elif field_name == 'research':
        # 去除常见前缀
        value = re.sub(
            r'^(研究方向[：:]|研究领域[：:]|研究方向|研究领域|'
            r'主要研究方向[：:]|学术方向[：:])',
            '',
            value,
        ).strip()

    elif field_name == 'phone':
        # 只保留第一个匹配的电话号码
        phone_match = re.search(
            r'(?:电话[：:]\s*)?(\d{3,4}[-]\d{7,8}|\d{11})',
            value,
        )
        if phone_match:
            value = phone_match.group(1).strip()

    return value.strip()


def _clean_text(text: str) -> str:
    """
    作用: 清洗文本：合并空白、去除首尾空格
    """
    if not text:
        return ''
    # 合并连续空白为单个空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _is_valid_email(email: str) -> bool:
    """
    作用: 验证邮箱格式是否合法
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
