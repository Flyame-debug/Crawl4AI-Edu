"""
文件名: fallback.py
作用: 非结构化兜底提取 —— 当 CSS 选择器模板匹配失败时，使用 jieba 分词 + 正则提取
主要功能:
    1. 基于 jieba 分词 + 职称词典匹配提取教师信息
    2. 正则提取邮箱、电话号码
    3. 根据页面内容推断 page_type
    4. 返回标准化的 extracted_data 结构
"""

import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger('apps')

# ============================================================
# 职称词典（用于 jieba 匹配和关键词扫描）
# ============================================================
# 核心职称（学术等级头衔），匹配优先级高于附加角色
CORE_TITLES = [
    '教授级高级工程师', '中国科学院院士', '中国工程院院士',
    '讲座教授', '名誉教授', '客座教授', '助理教授', '副教授', '教授',
    '副研究员', '助理研究员', '研究员',
    '高级工程师', '高级讲师', '工程师', '讲师',
    '院士', '助教',
]

# 附加角色/身份（导师、行政职务、荣誉头衔等），核心职称匹配失败时降级使用
EXTRA_TITLES = [
    '博士生导师', '硕士生导师', '学科带头人',
    '长江学者', '访问学者', '青年千人',
    '副院长', '系主任', '千人计划',
    '院长', '博导', '硕导', '博士后',
    '杰青', '优青', '博士', '硕士',
]

# 合并词典（用于需要全量匹配的场景，如关键词密度检测）
TITLE_DICT = CORE_TITLES + EXTRA_TITLES

# ============================================================
# 页面类型关键词（用于推断 page_type）
# ============================================================
PAGE_TYPE_KEYWORDS = {
    'teacher': [
        '教授', '副教授', '讲师', '教师', '导师', '研究员',
        '办公电话', '办公室', '电子邮箱', '研究方向', '个人简介',
        '教育背景', '工作经历', '学术兼职', '教师简介',
    ],
    'course': [
        '课程名称', '课程编号', '学分', '学时', '课程简介',
        '教学大纲', '教材', '参考书目', '考核方式', '先修课程',
        '授课教师', '上课时间', '上课地点', '开课学期', '选课',
    ],
    'research': [
        '论文标题', '摘要', '关键词', '发表期刊', 'DOI',
        '基金项目', '引用', '参考文献', '出版年份', '卷期',
        '收录', '影响因子', '学术论文', '科研成果',
    ],
}


def fallback_extract(markdown: str, page_type_hint: str = None) -> Dict[str, Any]:
    """
    作用: 非结构化兜底提取，使用 jieba 分词 + 正则从 Markdown 文本中提取信息

    处理流程:
        1. 尝试使用 jieba 分词扫描职称关键词
        2. 用正则提取邮箱和电话
        3. 根据关键词密度推断 page_type
        4. 组装各类型的 extracted 字段

    参数:
        markdown: 已转换的 Markdown 文本
        page_type_hint: 成员A预填的 page_type 值（如 teacher/course/research）

    返回:
        标准 extracted_data 结构：
        {
            'page_type': str,
            'extracted': dict,
            'confidence': float,
            'method': 'fallback',
        }
    """
    if not markdown or not markdown.strip():
        return {
            'page_type': 'unknown',
            'extracted': {},
            'confidence': 0.0,
            'method': 'fallback',
        }

    # 推断或使用预填的 page_type
    detected_type = _detect_page_type(markdown)
    page_type = detected_type if detected_type != 'unknown' else (page_type_hint or 'unknown')

    # 通用提取：邮箱、电话
    emails = _extract_emails(markdown)
    phones = _extract_phones(markdown)

    # 按 page_type 提取特定字段
    if page_type == 'teacher':
        extracted = _extract_teacher_fields(markdown, emails, phones)
        confidence = _calculate_teacher_confidence(extracted)
    elif page_type == 'course':
        extracted = _extract_course_fields(markdown, emails, phones)
        confidence = _calculate_generic_confidence(extracted)
    elif page_type == 'research':
        extracted = _extract_research_fields(markdown)
        confidence = _calculate_generic_confidence(extracted)
    else:
        extracted = {}
        confidence = 0.0

    logger.info(
        f'兜底提取完成: page_type={page_type}, '
        f'置信度={confidence}, 检测类型={detected_type}'
    )

    return {
        'page_type': page_type,
        'extracted': extracted,
        'confidence': confidence,
        'method': 'fallback',
    }


def _detect_page_type(markdown: str) -> str:
    """
    作用: 根据关键词密度推断页面类型
    """
    scores = {}
    markdown_lower = markdown.lower()

    for ptype, keywords in PAGE_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in markdown_lower)
        scores[ptype] = score

    if not scores:
        return 'unknown'

    best_type = max(scores, key=scores.get)
    if scores[best_type] >= 2:
        return best_type

    return 'unknown'


def _extract_emails(text: str) -> List[str]:
    """
    作用: 用正则提取文本中的邮箱地址
    """
    # 匹配标准邮箱格式，排除中文域名等无效情况
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    seen = set()
    result = []
    for email in matches:
        email = email.strip().rstrip('.')
        if email not in seen and len(email) < 100:
            seen.add(email)
            result.append(email)
    return result


def _extract_phones(text: str) -> List[str]:
    """
    作用: 用正则提取文本中的中国手机号和座机号
    """
    phones = []

    # 中国手机号：1 开头的 11 位数字
    mobile_pattern = r'1[3-9]\d{9}'
    for match in re.finditer(mobile_pattern, text):
        phones.append(match.group(0))

    # 座机号：区号-号码 格式
    landline_pattern = r'(?:0\d{2,3}[-])?\d{7,8}'
    for match in re.finditer(landline_pattern, text):
        phones.append(match.group(0))

    # 去重
    seen = set()
    result = []
    for phone in phones:
        if phone not in seen:
            seen.add(phone)
            result.append(phone)

    return result[:3]  # 最多返回3个号码


def _extract_teacher_fields(
    markdown: str, emails: List[str], phones: List[str]
) -> Dict[str, Any]:
    """
    作用: 从 Markdown 文本中提取教师信息
    """
    extracted = {}

    # 姓名：尝试从标题行中提取
    name = _extract_name_from_markdown(markdown)
    extracted['name'] = name or ''

    # 职称：关键词匹配
    title = _extract_title_from_text(markdown)
    extracted['title'] = title or ''

    # 院系：关键词附近提取
    department = _extract_keyword_nearby(markdown, ['院系', '学院', '系', '部门', '单位', '所属'])
    extracted['department'] = department or ''

    # 研究方向：关键词附近提取
    research = _extract_keyword_nearby(
        markdown, ['研究方向', '研究领域', '研究兴趣', '科研方向']
    )
    extracted['research'] = research or ''

    # 邮箱：取第一个
    extracted['email'] = emails[0] if emails else ''

    # 电话：取第一个
    extracted['phone'] = phones[0] if phones else ''

    # 办公室：关键词附近提取
    office = _extract_keyword_nearby(markdown, ['办公室', '办公地点', '地址', '房间'])
    extracted['office'] = office or ''

    return extracted


def _extract_course_fields(
    markdown: str, emails: List[str], phones: List[str]
) -> Dict[str, Any]:
    """
    作用: 从 Markdown 文本中提取课程信息
    """
    extracted = {}

    # 课程名：从标题中提取
    name = _extract_name_from_markdown(markdown)
    extracted['course_name'] = name or ''

    # 授课教师：关键词附近提取
    teacher = _extract_keyword_nearby(markdown, ['授课教师', '任课教师', '主讲教师', '教师'])
    extracted['teacher'] = teacher or ''

    # 学分：数字匹配
    credits = _extract_number_nearby(markdown, ['学分'])
    extracted['credits'] = credits

    # 学时：数字匹配
    hours = _extract_number_nearby(markdown, ['学时', '课时'])
    extracted['hours'] = hours

    # 课程简介：段落匹配
    syllabus = _extract_keyword_nearby(
        markdown, ['课程简介', '课程描述', '课程介绍', '内容简介'], max_chars=500
    )
    extracted['syllabus'] = syllabus or ''

    # 学期：关键词匹配
    semester = _extract_keyword_nearby(markdown, ['学期', '开课学期', '学年'])
    extracted['semester'] = semester or ''

    return extracted


def _extract_research_fields(markdown: str) -> Dict[str, Any]:
    """
    作用: 从 Markdown 文本中提取科研/论文信息
    """
    extracted = {}

    # 论文标题：从标题中提取
    title = _extract_name_from_markdown(markdown)
    extracted['paper_title'] = title or ''

    # 作者：关键词附近提取
    authors = _extract_keyword_nearby(markdown, ['作者', '作者信息', '作 者'])
    extracted['authors'] = _parse_authors(authors)

    # 期刊：关键词附近提取
    journal = _extract_keyword_nearby(markdown, ['期刊', '发表', '杂志', '刊物', '出处'])
    extracted['journal'] = journal or ''

    # 年份：正则匹配
    year_match = re.search(r'(?:19|20)\d{2}', markdown)
    extracted['year'] = int(year_match.group(0)) if year_match else None

    # DOI：正则匹配
    doi_match = re.search(r'(?:doi|DOI)[:：]?\s*(10\.\d{4,}/[^\s]+)', markdown)
    extracted['doi'] = doi_match.group(1) if doi_match else ''

    return extracted


# ============================================================
# 辅助提取函数
# ============================================================


def _extract_name_from_markdown(markdown: str) -> Optional[str]:
    """
    作用: 从 Markdown 文本的标题行中尝试提取名称

    策略：
        1. 取第一个一级标题（# xxx）
        2. 若没有，取第一个二级标题（## xxx）
        3. 限制长度，过滤过短的字母串
    """
    # 尝试一级标题
    h1_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
    if h1_match:
        name = h1_match.group(1).strip()
        # 过滤明显的非人名标题（太长或纯英文/数字）
        if len(name) <= 30 and not re.match(r'^[A-Za-z\s\d]+$', name):
            return name

    # 尝试二级标题
    h2_match = re.search(r'^##\s+(.+)$', markdown, re.MULTILINE)
    if h2_match:
        name = h2_match.group(1).strip()
        if len(name) <= 30:
            return name

    return None


def _extract_title_from_text(text: str) -> Optional[str]:
    """
    作用: 在文本中按优先级匹配职称关键词

    匹配策略：
        1. 先在核心职称（CORE_TITLES）中按长度降序匹配，
           长词优先可避免子串误匹配（如"副教授"优先于"教授"）。
        2. 核心职称未命中时，降级到附加角色（EXTRA_TITLES），
           同样按长度降序匹配。
    """
    # 第一级：匹配核心职称（按长度降序）
    sorted_core = sorted(CORE_TITLES, key=len, reverse=True)
    for title in sorted_core:
        if title in text:
            return title

    # 第二级：降级匹配附加角色（按长度降序）
    sorted_extra = sorted(EXTRA_TITLES, key=len, reverse=True)
    for title in sorted_extra:
        if title in text:
            return title

    return None


def _extract_keyword_nearby(
    text: str, keywords: List[str], max_chars: int = 200
) -> Optional[str]:
    """
    作用: 在文本中找到关键词所在行或段落，返回其后的文本内容

    参数:
        text: 全文
        keywords: 要搜索的关键词列表
        max_chars: 返回的最大字符数
    """
    lines = text.split('\n')

    for i, line in enumerate(lines):
        for kw in keywords:
            if kw in line:
                # 优先尝试在同行中提取关键词之后的内容
                idx = line.find(kw)
                suffix = line[idx + len(kw):].strip()
                # 去除冒号等分隔符
                suffix = re.sub(r'^[：:：\s]+', '', suffix)

                if suffix and len(suffix) > 1:
                    return suffix[:max_chars].strip()

                # 如果同行无内容，取下一行
                if i + 1 < len(lines) and lines[i + 1].strip():
                    return lines[i + 1].strip()[:max_chars]

    return None


def _extract_number_nearby(text: str, keywords: List[str]) -> Optional[int]:
    """
    作用: 在关键词附近提取数字（如学分、学时）
    """
    for kw in keywords:
        # 关键词后的数字
        pattern = rf'{kw}[：:：\s]*(\d+(?:\.\d+)?)'
        match = re.search(pattern, text)
        if match:
            try:
                return int(float(match.group(1)))
            except ValueError:
                continue

    return None


def _parse_authors(author_text: str) -> List[str]:
    """
    作用: 解析作者字符串为列表
    """
    if not author_text:
        return []

    # 按常见分隔符拆分
    authors = re.split(r'[,，;；、\s]+', author_text)
    return [a.strip() for a in authors if a.strip() and len(a.strip()) >= 2]


def _calculate_teacher_confidence(extracted: Dict[str, Any]) -> float:
    """
    作用: 计算教师信息提取的置信度

    评分规则：
        - 有姓名：+0.3
        - 有职称：+0.3
        - 有院系：+0.1
        - 有邮箱：+0.1
        - 有研究方向：+0.1
        - 有电话/办公室：+0.1
    """
    score = 0.0
    if extracted.get('name'):
        score += 0.3
    if extracted.get('title'):
        score += 0.3
    if extracted.get('department'):
        score += 0.1
    if extracted.get('email'):
        score += 0.1
    if extracted.get('research'):
        score += 0.1
    if extracted.get('phone') or extracted.get('office'):
        score += 0.1

    return round(score, 2)


def _calculate_generic_confidence(extracted: Dict[str, Any]) -> float:
    """
    作用: 计算通用类型提取的置信度

    评分规则：已填充字段数 / 总字段数
    """
    if not extracted:
        return 0.0

    total = len(extracted)
    filled = sum(1 for v in extracted.values() if v)
    return round(filled / max(total, 1), 2)
