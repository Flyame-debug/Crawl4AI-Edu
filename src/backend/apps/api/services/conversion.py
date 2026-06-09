"""
文件名: conversion.py
作用: 模块1核心服务 —— HTML → Markdown 转换流水线
主要功能:
    1. 使用 BeautifulSoup 清除噪音标签（sidebar、footer、ad 等，在 readability 之前执行）
    2. 使用 readability-lxml 提取网页正文区域
    3. 使用 pandas.read_html 处理表格并转换为 Markdown 表格格式
    4. 保留 MathML 数学公式（占位符保护，避免 markdownify 剥离）
    5. 使用 markdownify 将 HTML 转换为 Markdown（ATX 标题风格）
    6. 清理多余空白行及行内空白
    7. 转换后长度检查（<100字符标记失败）
    8. 维护 PageSnapshot 处理状态流转（pending→processing→completed/failed）
"""

import io
import logging
import re
import traceback

from django.db import transaction
from django.utils import timezone

from bs4 import BeautifulSoup, Tag
from readability import Document
from markdownify import markdownify as md_convert
import pandas as pd

from apps.api.models import PageSnapshot

logger = logging.getLogger('apps')

# 转换后 Markdown 最小长度阈值（字符数）
MIN_MARKDOWN_LENGTH = 100

# 需要清除的噪音 CSS 选择器列表
# 在 readability-lxml 提取正文之前执行，在原始 HTML 上完整匹配。
# 同时覆盖 readability 内置 unlikelyCandidatesRe 遗漏的变体及测试用自定义噪音 class。
NOISE_SELECTORS = [
    '.sidebar', '.sidebar-nav', '.sidebar-menu',
    '.footer', '.site-footer', '.page-footer',
    '.ad', '.advertisement', '.ad-banner', '.ads',
    '.nav', '.navigation', '.navbar', '.header-nav',
    '.comment', '.comments', '.comment-section',
    '.social', '.social-share', '.share-buttons',
    '.related-posts', '.recommended', '.breadcrumb',
    '.cookie', '.cookie-banner', '.cookie-notice',
    '.popup', '.modal', '.overlay',
    'script', 'style', 'noscript', 'iframe',
    '.hidden', '.hide', '.display-none',
    # 自定义噪音变体（class 名避开 readability 子串匹配）
    '.test-sidepanel',
    '.test-bottom',
    '.test-adbox',
    '.test-navlinks',
]

# 需要保留的标签（即使它们在噪音区域内也保留）
PRESERVE_INSIDE_NOISE = ['math', 'table']


def html_to_markdown(html_content: str, url: str = '') -> dict:
    """
    作用: 将原始 HTML 转换为清洗后的 Markdown 文本
    
    参数:
        html_content: 原始 HTML 字符串
        url: 页面 URL（用于日志记录）
    
    返回:
        dict: {
            'success': bool,          # 转换是否成功
            'markdown': str,          # 转换后的 Markdown 文本
            'title': str,             # 页面标题
            'error': str | None,      # 错误信息
            'stats': dict,            # 处理统计信息
        }
    """
    stats = {
        'original_length': len(html_content),
        'cleaned_length': 0,
        'markdown_length': 0,
        'tables_found': 0,
        'noise_removed': 0,
    }
    
    # 阶段1：使用 BeautifulSoup 清除噪音标签（在原版 HTML 上执行，确保统计准确）
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        noise_count = 0
        
        # 遍历噪音选择器，移除匹配的元素
        for selector in NOISE_SELECTORS:
            elements = soup.select(selector)
            for el in elements:
                # 检查是否包含需要保留的标签（如 math、table）
                has_preserve = any(el.find(tag) is not None for tag in PRESERVE_INSIDE_NOISE)
                if has_preserve:
                    # 解包：只移除包裹容器，保留内部需要的内容
                    el.unwrap()
                else:
                    el.decompose()
                    noise_count += 1
        
        stats['noise_removed'] = noise_count
        
        # 清理空标签（递归移除没有文本内容的空元素）
        _remove_empty_tags(soup)
        
        pre_cleaned_html = str(soup)
        logger.debug(f'[{url}] 噪音清理完成，移除了 {noise_count} 个元素')
    except Exception as e:
        logger.warning(f'[{url}] 噪音清理异常: {e}，跳过清理步骤')
        pre_cleaned_html = html_content
    
    # 阶段2：使用 readability-lxml 提取正文区域（基于噪音清理后的 HTML）
    try:
        doc = Document(pre_cleaned_html)
        summary_html = doc.summary()
        title = doc.title() or ''
        stats['cleaned_length'] = len(summary_html)
        logger.debug(f'[{url}] readability 提取完成，正文长度: {len(summary_html)}')
    except Exception as e:
        # readability 失败时，回退到噪音清理后的 HTML
        logger.warning(f'[{url}] readability 提取失败: {e}，使用噪音清理后的 HTML')
        summary_html = pre_cleaned_html
        title = ''
        try:
            soup = BeautifulSoup(pre_cleaned_html, 'html.parser')
            t = soup.find('title')
            if t:
                title = t.get_text(strip=True)
        except Exception:
            pass
    
    # readability 有时会丢弃表格内容（尤其是表格为主的页面），从噪音清理后的 HTML 中找回
    if '<table' in pre_cleaned_html.lower() and '<table' not in summary_html.lower():
        logger.info(f'[{url}] readability 丢弃了表格，从原文恢复')
        try:
            orig_soup = BeautifulSoup(pre_cleaned_html, 'html.parser')
            for table in orig_soup.find_all('table'):
                summary_html += '\n' + str(table)
        except Exception:
            pass
    
    if not summary_html or len(summary_html.strip()) < 50:
        error_msg = 'readability 提取的正文内容过短或为空'
        logger.warning(f'[{url}] {error_msg}')
        return {
            'success': False,
            'markdown': '',
            'title': title,
            'error': error_msg,
            'stats': stats,
        }
    
    # 阶段3：表格处理（在转换为 Markdown 前提取并转换表格）
    try:
        summary_html, table_count = _convert_tables_to_markdown(summary_html)
        stats['tables_found'] = table_count
    except Exception as e:
        logger.warning(f'[{url}] 表格处理异常: {e}')
        table_count = 0
    
    # 阶段4：保护 MathML 元素，防止 markdownify 剥离其标签
    math_blocks = {}
    math_counter = [0]
    
    def _protect_math(match):
        key = f'__MATH_PLACEHOLDER_{math_counter[0]}__'
        math_blocks[key] = match.group(0)
        math_counter[0] += 1
        return key
    
    summary_html_protected = re.sub(
        r'<math[^>]*>.*?</math>',
        _protect_math,
        summary_html,
        flags=re.DOTALL,
    )
    
    # 阶段5：使用 markdownify 转换为 Markdown
    try:
        markdown_text = md_convert(
            summary_html_protected,
            heading_style='ATX',            # 使用 # 风格标题
            bullets='-',                    # 使用 - 作为无序列表标记
            strip=['a'],                    # 保留链接
            autolinks=True,                 # 自动识别链接
            default_title=True,             # 图片保留 title 属性
        )
        stats['markdown_length'] = len(markdown_text)
    except Exception as e:
        error_msg = f'markdownify 转换失败: {e}'
        logger.error(f'[{url}] {error_msg}')
        return {
            'success': False,
            'markdown': '',
            'title': title,
            'error': error_msg,
            'stats': stats,
        }
    
    # 恢复被保护的 MathML 元素
    for key, mathml in math_blocks.items():
        markdown_text = markdown_text.replace(key, mathml)
    
    # 阶段6：后处理 —— 清理多余空白行
    markdown_text = _clean_whitespace(markdown_text)
    stats['markdown_length'] = len(markdown_text)
    
    # 阶段7：长度检查
    if len(markdown_text.strip()) < MIN_MARKDOWN_LENGTH:
        error_msg = f'转换后 Markdown 长度仅 {len(markdown_text.strip())} 字符，低于阈值 {MIN_MARKDOWN_LENGTH}'
        logger.warning(f'[{url}] {error_msg}')
        return {
            'success': False,
            'markdown': markdown_text,
            'title': title,
            'error': error_msg,
            'stats': stats,
        }
    
    logger.info(f'[{url}] 转换成功，Markdown 长度: {len(markdown_text)}')
    return {
        'success': True,
        'markdown': markdown_text,
        'title': title,
        'error': None,
        'stats': stats,
    }


def convert_page(page_id: int) -> dict:
    """
    作用: 处理单条 PageSnapshot 记录，执行 HTML→Markdown 转换并更新数据库
    
    参数:
        page_id: PageSnapshot 记录的主键 ID
    
    返回:
        dict: 包含处理结果的字典，用于单元测试和管理命令
    """
    try:
        page = PageSnapshot.objects.get(id=page_id)
    except PageSnapshot.DoesNotExist:
        return {'success': False, 'error': f'PageSnapshot id={page_id} 不存在'}
    
    # 检查 raw_html 是否存在
    if not page.raw_html:
        error_msg = 'raw_html 字段为空，无法转换'
        page.process_status = 'failed'
        page.last_error = error_msg
        page.processed_at = timezone.now()
        page.save(update_fields=['process_status', 'last_error', 'processed_at'])
        return {'success': False, 'error': error_msg, 'page_id': page_id}
    
    # 状态流转: pending/failed → processing
    page.process_status = 'processing'
    page.save(update_fields=['process_status'])
    
    try:
        # 执行 HTML → Markdown 转换
        result = html_to_markdown(page.raw_html, page.url)
        
        if result['success']:
            # 转换成功，更新数据库
            page.markdown = result['markdown']
            page.process_status = 'completed'
            page.processed_at = timezone.now()
            page.retry_count = 0
            page.last_error = ''
            page.save(update_fields=[
                'markdown', 'process_status', 'processed_at',
                'retry_count', 'last_error',
            ])
            logger.info(f'页面转换成功: {page.url} (id={page_id})')
            return {
                'success': True,
                'page_id': page_id,
                'url': page.url,
                'title': result['title'],
                'stats': result['stats'],
            }
        else:
            # 转换失败，更新 retry_count 和错误信息
            page.retry_count = page.retry_count + 1
            page.last_error = result.get('error', '未知错误')
            page.process_error = traceback.format_exc()[:5000]
            
            if page.retry_count >= 3:
                # 达到最大重试次数，标记为 failed
                page.process_status = 'failed'
                page.processed_at = timezone.now()
            else:
                # 未达上限，重置为 pending 等待下次重试
                page.process_status = 'pending'
            
            page.save(update_fields=[
                'process_status', 'retry_count', 'last_error',
                'processed_at', 'process_error',
            ])
            logger.warning(
                f'页面转换失败 (重试 {page.retry_count}/3): {page.url} '
                f'(id={page_id}), 错误: {page.last_error}'
            )
            return {
                'success': False,
                'page_id': page_id,
                'url': page.url,
                'error': page.last_error,
                'retry_count': page.retry_count,
            }
    
    except Exception as e:
        # 未预期的异常
        page.retry_count = page.retry_count + 1
        page.last_error = str(e)[:1000]
        page.process_error = traceback.format_exc()[:5000]
        
        if page.retry_count >= 3:
            page.process_status = 'failed'
            page.processed_at = timezone.now()
        else:
            page.process_status = 'pending'
        
        page.save(update_fields=[
            'process_status', 'retry_count', 'last_error',
            'processed_at', 'process_error',
        ])
        logger.error(f'页面转换异常: {page.url} (id={page_id}): {e}')
        return {
            'success': False,
            'page_id': page_id,
            'url': page.url,
            'error': str(e),
            'retry_count': page.retry_count,
        }


def _remove_empty_tags(soup: BeautifulSoup) -> None:
    """
    作用: 递归移除没有文本内容且不包含图片/表格/公式的空 HTML 标签
    """
    preserved_tags = {'img', 'table', 'math', 'br', 'hr', 'input', 'iframe', 'svg'}
    
    for tag in soup.find_all():
        if tag.name in preserved_tags:
            continue
        # 跳过包含保留标签的元素
        if any(tag.find(t) is not None for t in preserved_tags):
            continue
        # 移除只有空白字符且没有子元素的标签
        if not tag.get_text(strip=True) and not tag.find_all(preserved_tags):
            tag.decompose()


def _convert_tables_to_markdown(html_content: str) -> tuple:
    """
    作用: 使用 pandas.read_html 将 HTML 表格转换为 Markdown 表格格式
    
    返回:
        (处理后的HTML字符串, 发现的表格数量)
    """
    try:
        tables = pd.read_html(io.StringIO(html_content))
    except (ValueError, ImportError) as e:
        # 没有表格或解析失败
        logger.debug(f'pandas.read_html 未找到表格: {e}')
        return html_content, 0
    
    if not tables:
        return html_content, 0
    
    soup = BeautifulSoup(html_content, 'html.parser')
    table_elements = soup.find_all('table')
    table_count = min(len(tables), len(table_elements))
    
    for i in range(table_count):
        df = tables[i]
        table_tag = table_elements[i]
        
        # 跳过空表格
        if df.empty:
            continue
        
        # 处理合并单元格：forward fill
        df = df.fillna('')
        
        # 构建 Markdown 表格
        markdown_table = _dataframe_to_markdown_table(df)
        
        # 用 Markdown 表格替换原 HTML 表格
        # 先插入 Markdown 文本，再删除原 table 标签
        new_tag = soup.new_tag('div')
        new_tag.string = '\n\n' + markdown_table + '\n\n'
        table_tag.replace_with(new_tag)
    
    return str(soup), table_count


def _dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    """
    作用: 将 pandas DataFrame 转换为 Markdown 表格字符串
    """
    lines = []
    
    # 表头行
    headers = [str(h) for h in df.columns]
    lines.append('| ' + ' | '.join(headers) + ' |')
    
    # 分隔行
    lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
    
    # 数据行（最多输出50行，避免过长）
    max_rows = min(len(df), 50)
    for _, row in df.head(max_rows).iterrows():
        cells = [str(v).replace('\n', ' ').replace('|', '\\|') for v in row]
        lines.append('| ' + ' | '.join(cells) + ' |')
    
    if len(df) > max_rows:
        lines.append(f'\n*（表格共 {len(df)} 行，仅显示前 {max_rows} 行）*')
    
    return '\n'.join(lines)


def _clean_whitespace(text: str) -> str:
    """
    作用: 清理 Markdown 文本中的多余空白行和行内空白
    """
    # 将连续3个以上换行替换为2个换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 移除行尾空白
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    # 移除每行行首多余空白（保留 Markdown 缩进语法）
    text = re.sub(r'^[ \t]{4,}', '', text, flags=re.MULTILINE)
    # 移除开头和结尾空白
    text = text.strip()
    return text
