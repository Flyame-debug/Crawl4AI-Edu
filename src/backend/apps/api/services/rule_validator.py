"""
文件名: rule_validator.py
作用: 模块4核心 —— 规则兜底校验（三步分层校验 + 纯规则兜底提取）
主要功能:
    1. 对 AI 提取结果进行正则格式校验、词典匹配、遗漏补充
    2. AI 不可用时使用纯规则（正则+词典）完成兜底提取
    3. 输出结构与模块3保持一致（page_type + content(Markdown) + method + confidence）
    4. 校验结果写入 _validation 字段，嵌入 extracted_data 一起入库
调用方: cleaning_pipeline.py / tasks.py
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger('apps.api.services.rule_validator')

# ============================================================
# 常量配置
# ============================================================

# 邮箱正则：标准邮箱格式
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# 手机号正则：中国大陆手机号（1 开头的 11 位数字）
MOBILE_PATTERN = re.compile(r'1[3-9]\d{9}')

# 座机号正则：区号 + 号码（含连字符或空格）
LANDLINE_PATTERN = re.compile(
    r'(?:0\d{2,3}[-—\s]?)\d{7,8}'
    r'|'
    r'\d{3,4}[-—\s]\d{7,8}'
)

# 无效/占位邮箱前缀（用于过滤脏数据）
INVALID_EMAIL_PREFIXES = [
    'example', 'test@test', 'xxx', 'unknown', 'none',
    'email', 'noreply', 'no-reply', 'admin@admin',
]

# 松散邮箱正则：用于捕捉格式不完整的邮箱（如缺少顶级域名），供校验步骤使用
LOOSE_EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+')

# 松散电话正则：用于捕捉短数字串等疑似电话尝试（3-6位纯数字，可能为截断号码）
LOOSE_PHONE_PATTERN = re.compile(r'\b\d{3,6}\b')

# 无效/占位电话前缀（用于过滤脏数据）
INVALID_PHONE_PATTERNS = [
    r'^0{8,}$', r'^1{8,}$', r'^12345678',
    r'^000', r'^111', r'^99+',
]

# 置信度阈值
CONFIDENCE_HIGH_FIELDS = 5      # 教师页提取到 ≥5 个字段 → high
CONFIDENCE_MEDIUM_FIELDS = 3    # 教师页提取到 ≥3 个字段 → medium
CONFIDENCE_GENERIC_HIGH = 4     # 通用页提取到 ≥4 个字段 → high
CONFIDENCE_GENERIC_MEDIUM = 2   # 通用页提取到 ≥2 个字段 → medium


# ============================================================
# 词典定义 — 职称（核心 + 附加，按长度降序避免子串误匹配）
# ============================================================

CORE_TITLES = [
    '教授级高级工程师', '中国科学院院士', '中国工程院院士',
    '讲座教授', '名誉教授', '客座教授', '助理教授', '副教授', '教授',
    '副研究员', '助理研究员', '研究员',
    '高级工程师', '高级讲师', '工程师', '讲师',
    '教授级高工', '研究员级高工',
    '院士', '助教', '特聘教授',
]

EXTRA_TITLES = [
    '博士生导师', '硕士生导师', '学科带头人',
    '长江学者特聘教授', '青年长江学者', '访问学者',
    '青年千人', '千人计划', '杰出青年', '优秀青年',
    '博导', '硕导', '博士后',
    '杰青', '优青',
    '博士', '硕士', '学士',
]

# 按长度降序排列（长词优先匹配，避免"副教授"被"教授"误匹配）
SORTED_CORE_TITLES = sorted(CORE_TITLES, key=len, reverse=True)
SORTED_EXTRA_TITLES = sorted(EXTRA_TITLES, key=len, reverse=True)
ALL_TITLES = sorted(CORE_TITLES + EXTRA_TITLES, key=len, reverse=True)

# ============================================================
# 词典定义 — 学位
# ============================================================

DEGREE_DICT = ['博士', '硕士', '学士', '博士后']

# ============================================================
# 词典定义 — 院系关键词
# ============================================================

DEPARTMENT_KEYWORDS = [
    '学院', '系', '研究所', '中心', '实验室',
    '研究院', '学部', '教研室', '教学部', '研究中心',
]

# ============================================================
# 词典定义 — 页面类型关键词（用于推断 page_type）
# ============================================================

PAGE_TYPE_KEYWORDS = {
    'teacher': [
        '教授', '副教授', '讲师', '教师', '导师', '研究员',
        '办公电话', '办公室', '电子邮箱', '研究方向', '个人简介',
        '教育背景', '工作经历', '学术兼职', '教师简介', '师资',
    ],
    'course': [
        '课程名称', '课程编号', '学分', '学时', '课程简介',
        '教学大纲', '教材', '参考书目', '考核方式', '先修课程',
        '授课教师', '上课时间', '上课地点', '开课学期', '选课',
    ],
    'research': [
        '论文标题', '摘要', '关键词', '发表期刊', 'DOI',
        '基金项目', '引用', '参考文献', '出版年份',
        '收录', '影响因子', '学术论文', '科研成果',
    ],
}


# ============================================================
# 公开函数：三步分层校验
# ============================================================

def validate_with_rules(
    ai_result: Dict[str, Any],
    markdown: str = None
) -> Dict[str, Any]:
    """
    作用: 对 AI 提取结果进行三步分层校验 —— 提取字段、格式校验、补充遗漏

    三步流程:
        Step 1: 从 AI content Markdown 和原始 markdown 中提取结构化字段
        Step 2: 逐字段格式校验 + 词典匹配，发现问题从原文修正
        Step 3: 补充遗漏字段（原文有但 AI 没提的）→ 组装修正后的 content

    参数:
        ai_result: 模块3的 ai_clean_and_extract().data，结构为:
            {page_type, content (Markdown), method, confidence}
        markdown: 原始 Markdown 文本（用于正则二次提取和比对）

    返回:
        校验并修正后的结果，结构为:
        {
            page_type, content (修正后Markdown), method, confidence,
            _validation: {passed, fixes, warnings}
        }
        method 在有修正时由 "ai_ollama" 变为 "ai_ollama_fixed"
    """
    if not ai_result:
        logger.warning("AI结果为None，跳过规则校验")
        return {
            "page_type": "unknown",
            "content": "",
            "method": "extraction_error",
            "confidence": "low",
            "_validation": {"passed": False, "fixes": [], "warnings": ["AI结果为空"]},
        }

    ai_content = ai_result.get("content", "")
    page_type = ai_result.get("page_type", "unknown")
    method = ai_result.get("method", "ai_ollama")
    confidence = ai_result.get("confidence", "low")
    source_markdown = markdown or ""

    fixes: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    # ============================================================
    # Step 1: 从 AI content 和原始 markdown 中提取结构化字段
    # ============================================================
    ai_emails = _extract_emails(ai_content)
    ai_phones = _extract_phones(ai_content)
    ai_titles = _extract_titles_from_text(ai_content)

    raw_emails = _extract_emails(source_markdown) if source_markdown else []
    raw_phones = _extract_phones(source_markdown) if source_markdown else []
    raw_titles = _extract_titles_from_text(source_markdown) if source_markdown else []

    # ============================================================
    # Step 2: 逐字段格式校验 + 词典匹配
    # ============================================================
    content_modified = ai_content

    # 2.1 邮箱校验
    for email in ai_emails:
        if not _is_valid_email(email):
            # 格式不对 → 尝试从原文找有效邮箱替换
            valid_email = next((e for e in raw_emails if _is_valid_email(e)), None)
            if valid_email and valid_email != email:
                content_modified = content_modified.replace(email, valid_email)
                fixes.append({"field": "email", "original": email, "corrected": valid_email})
            else:
                # 原文也没有有效邮箱 → 去掉无效邮箱
                content_modified = _remove_invalid_field_from_markdown(
                    content_modified, "邮箱", email
                )
                warnings.append({"field": "email", "message": f"邮箱格式无效且原文无有效邮箱: {email}"})

    # 2.1b 松散邮箱扫描：捕捉严格正则漏掉的残缺邮箱（如缺少顶级域名）
    loose_emails = LOOSE_EMAIL_PATTERN.findall(ai_content)
    for email in loose_emails:
        email = email.strip().rstrip('.')
        if email in ai_emails:
            continue
        if not _is_valid_email(email):
            valid_email = next((e for e in raw_emails if _is_valid_email(e)), None)
            if valid_email:
                content_modified = content_modified.replace(email, valid_email)
                fixes.append({"field": "email", "original": email, "corrected": valid_email})

    # 2.2 AI 遗漏邮箱 → 从原文补充
    if not ai_emails and raw_emails:
        valid_raw = [e for e in raw_emails if _is_valid_email(e)]
        if valid_raw:
            content_modified += f"\n- 邮箱: {valid_raw[0]}"
            fixes.append({"field": "email", "original": None, "corrected": valid_raw[0]})

    # 2.3 电话校验
    for phone in ai_phones:
        if not _is_valid_phone(phone):
            valid_phone = next((p for p in raw_phones if _is_valid_phone(p)), None)
            if valid_phone and valid_phone != phone:
                content_modified = content_modified.replace(phone, valid_phone)
                fixes.append({"field": "phone", "original": phone, "corrected": valid_phone})
            else:
                content_modified = _remove_invalid_field_from_markdown(
                    content_modified, "电话", phone
                )
                warnings.append({"field": "phone", "message": f"电话格式无效且原文无有效电话: {phone}"})

    # 2.3b 松散电话扫描：捕捉严格正则漏掉的短数字串（疑似截断的电话号码）
    loose_phones = LOOSE_PHONE_PATTERN.findall(ai_content)
    # 收集 AI content 中已有的有效号码（含严格匹配和后续已修正的）
    existing_valid_phones = set(p for p in ai_phones if _is_valid_phone(p))
    existing_valid_phones.update(
        p for p in LOOSE_PHONE_PATTERN.findall(ai_content)
        if _is_valid_phone(p)
    )
    for phone in loose_phones:
        if phone in ai_phones:
            continue
        # 排除年份（如 2024、2025）和明显非电话数字
        if re.match(r'^(19|20)\d{2}$', phone):
            continue
        # 排除已是有效号码的子串（如 "010" 是 "010-12345678" 的子串）
        if any(phone in vp for vp in existing_valid_phones):
            continue
        if not _is_valid_phone(phone):
            valid_phone = next((p for p in raw_phones if _is_valid_phone(p)), None)
            if valid_phone:
                content_modified = content_modified.replace(phone, valid_phone)
                fixes.append({"field": "phone", "original": phone, "corrected": valid_phone})

    # 2.4 AI 遗漏电话 → 从原文补充
    if not ai_phones and raw_phones:
        valid_raw = [p for p in raw_phones if _is_valid_phone(p)]
        if valid_raw:
            content_modified += f"\n- 电话: {valid_raw[0]}"
            fixes.append({"field": "phone", "original": None, "corrected": valid_raw[0]})

    # 2.5 职称词典校验（仅记 warning，不强制修正，因为 AI 可能提取了更精准的描述）
    for title in ai_titles:
        if title not in ALL_TITLES:
            # 尝试从原文中匹配更准确的职称
            if raw_titles:
                better_title = raw_titles[0]
                if better_title != title:
                    # 替换 AI content 中的职称
                    content_modified = content_modified.replace(title, better_title)
                    fixes.append({"field": "title", "original": title, "corrected": better_title})
            else:
                warnings.append({
                    "field": "title",
                    "message": f"职称 '{title}' 不在教育词典中，可能是AI推断的非标准表述",
                })

    # 2.5b 非词典职称检测：扫描 AI content 标题行和职称指示词附近，识别词典外的疑似职称
    _detect_unknown_titles(ai_content, ALL_TITLES, ai_titles, warnings)

    # 2.6 AI 遗漏职称 → 从原文补充
    if not ai_titles and raw_titles:
        # 尝试在 content 开头的标题处插入职称
        inserted = _insert_field_into_content(content_modified, "职称", raw_titles[0])
        if inserted != content_modified:
            content_modified = inserted
            fixes.append({"field": "title", "original": None, "corrected": raw_titles[0]})

    # ============================================================
    # Step 3: 组装校验结果
    # ============================================================
    passed = len(fixes) == 0
    if fixes:
        method = "ai_ollama_fixed"

    logger.info(
        f"规则校验完成: fixes={len(fixes)}, warnings={len(warnings)}, "
        f"passed={passed}, method={method}"
    )

    return {
        "page_type": page_type,
        "content": content_modified,
        "method": method,
        "confidence": confidence,
        "_validation": {
            "passed": passed,
            "fixes": fixes,
            "warnings": warnings,
        },
    }


# ============================================================
# 公开函数：纯规则兜底提取（AI 不可用时）
# ============================================================

def extract_by_rules_fallback(
    markdown: str,
    page_type_hint: str = None
) -> Dict[str, Any]:
    """
    作用: AI 完全不可用时的纯规则兜底提取（正则 + 词典 + jieba）

    提取流程:
        1. 正则提取邮箱、电话
        2. 词典匹配职称、院系
        3. 关键词密度推断页面类型
        4. 按页面类型提取特定字段
        5. 组装为 Markdown content 输出

    参数:
        markdown: 原始 Markdown 文本
        page_type_hint: 成员A预填的页面类型，可选

    返回:
        {page_type, content (Markdown), method: "rule_fallback", confidence}
    """
    if not markdown or not markdown.strip():
        logger.warning("Fallback提取输入为空")
        return {
            "page_type": "unknown",
            "content": "",
            "method": "rule_fallback",
            "confidence": "low",
        }

    # 提取通用字段
    emails = _extract_emails(markdown)
    phones = _extract_phones(markdown)
    titles = _extract_titles_from_text(markdown)

    # 推断页面类型
    detected_type = _detect_page_type(markdown)
    page_type = detected_type if detected_type != "unknown" else (page_type_hint or "unknown")

    # 按页面类型做专项提取
    if page_type == "teacher":
        extracted, confidence = _extract_teacher_info(markdown, emails, phones, titles)
    elif page_type == "course":
        extracted, confidence = _extract_course_info(markdown, emails, phones)
    elif page_type == "research":
        extracted, confidence = _extract_research_info(markdown)
    else:
        extracted = _extract_generic_info(markdown, emails, phones, titles)
        confidence = "low"

    # 组装 Markdown content
    content = _build_fallback_content(extracted, page_type)

    logger.info(
        f"Fallback提取完成: page_type={page_type}, "
        f"confidence={confidence}, fields={len(extracted)}"
    )

    return {
        "page_type": page_type,
        "content": content,
        "method": "rule_fallback",
        "confidence": confidence,
    }


# ============================================================
# 字段提取辅助函数
# ============================================================

def _extract_emails(text: str) -> List[str]:
    """
    作用: 用正则从文本中提取所有邮箱地址
    """
    if not text:
        return []
    matches = EMAIL_PATTERN.findall(text)
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
    作用: 用正则从文本中提取中国手机号和座机号
    """
    if not text:
        return []
    phones = []

    # 手机号
    for match in MOBILE_PATTERN.finditer(text):
        phones.append(match.group(0))

    # 座机号
    for match in LANDLINE_PATTERN.finditer(text):
        phone = match.group(0).replace('—', '-').replace(' ', '-')
        phones.append(phone)

    # 去重
    seen = set()
    result = []
    for phone in phones:
        if phone not in seen:
            seen.add(phone)
            result.append(phone)

    return result[:5]  # 最多返回 5 个号码


def _extract_titles_from_text(text: str) -> List[str]:
    """
    作用: 按长词优先策略匹配职称关键词，返回匹配到的所有职称
    """
    if not text:
        return []
    titles = []
    for title in SORTED_CORE_TITLES:
        if title in text:
            titles.append(title)
    for title in SORTED_EXTRA_TITLES:
        if title in text and title not in titles:
            titles.append(title)
    return titles


def _extract_name_from_markdown(markdown: str) -> Optional[str]:
    """
    作用: 从 Markdown 标题行中提取名称

    策略:
        1. 取第一个一级标题（# xxx）
        2. 若没有，取第一个二级标题（## xxx）
        3. 过滤过长（>30字符）和纯英文/数字标题
    """
    if not markdown:
        return None

    # 尝试一级标题
    h1_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
    if h1_match:
        name = h1_match.group(1).strip()
        if len(name) <= 30 and not re.match(r'^[A-Za-z\s\d]+$', name):
            return name

    # 尝试二级标题
    h2_match = re.search(r'^##\s+(.+)$', markdown, re.MULTILINE)
    if h2_match:
        name = h2_match.group(1).strip()
        if len(name) <= 30:
            return name

    return None


def _extract_keyword_nearby(
    text: str,
    keywords: List[str],
    max_chars: int = 200
) -> Optional[str]:
    """
    作用: 在文本中找到关键词所在行，返回其后的内容

    参数:
        text: 全文
        keywords: 要搜索的关键词列表
        max_chars: 返回的最大字符数
    """
    if not text or not keywords:
        return None

    lines = text.split('\n')
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw in line:
                # 优先提取同行中关键词之后的内容
                idx = line.find(kw)
                suffix = line[idx + len(kw):].strip()
                suffix = re.sub(r'^[：:：\s]+', '', suffix)
                if suffix and len(suffix) > 1:
                    return suffix[:max_chars].strip()

                # 同行无内容，取下一行
                if i + 1 < len(lines) and lines[i + 1].strip():
                    return lines[i + 1].strip()[:max_chars]

    return None


def _extract_number_nearby(text: str, keywords: List[str]) -> Optional[int]:
    """
    作用: 在关键词附近提取数字（如学分、学时）
    """
    if not text or not keywords:
        return None
    for kw in keywords:
        pattern = rf'{kw}[：:：\s]*(\d+(?:\.\d+)?)'
        match = re.search(pattern, text)
        if match:
            try:
                return int(float(match.group(1)))
            except ValueError:
                continue
    return None


def _extract_department(text: str) -> Optional[str]:
    """
    作用: 通过院系关键词从文本中提取院系名称
    """
    if not text:
        return None
    for kw in DEPARTMENT_KEYWORDS:
        # 匹配关键词前的 2-8 个中文字符（如"计算机" + "学院"）
        pattern = rf'([\u4e00-\u9fa5]{{2,10}}{kw})'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


# ============================================================
# 格式校验辅助函数
# ============================================================

def _is_valid_email(email: str) -> bool:
    """
    作用: 校验邮箱地址格式是否合法
    """
    if not email or not isinstance(email, str):
        return False

    email = email.strip()

    # 长度检查
    if len(email) < 5 or len(email) > 254:
        return False

    # 检查是否为占位/无效邮箱
    email_lower = email.lower()
    for prefix in INVALID_EMAIL_PREFIXES:
        if email_lower.startswith(prefix):
            return False

    # 必须有且仅有一个 @
    if email.count('@') != 1:
        return False

    # 正则匹配
    if not EMAIL_PATTERN.fullmatch(email):
        return False

    # 域名部分至少有一个点
    local, domain = email.split('@')
    if '.' not in domain:
        return False

    # 顶级域名至少 2 个字符
    tld = domain.rsplit('.', 1)[-1]
    if len(tld) < 2:
        return False

    return True


def _is_valid_phone(phone: str) -> bool:
    """
    作用: 校验手机号或座机号格式是否合法
    """
    if not phone or not isinstance(phone, str):
        return False

    phone = phone.strip().replace('—', '-').replace(' ', '-')

    # 过滤明显的占位号码
    for pattern in INVALID_PHONE_PATTERNS:
        if re.match(pattern, phone):
            return False

    # 手机号：1 开头 11 位数字
    if MOBILE_PATTERN.fullmatch(phone):
        return True

    # 座机号：区号 + 号码
    if LANDLINE_PATTERN.fullmatch(phone):
        return True

    # 纯数字座机（无连字符）：7-12位数字
    if re.match(r'^\d{7,12}$', phone):
        return True

    return False


def _detect_unknown_titles(
    content: str,
    known_titles: List[str],
    already_extracted: List[str],
    warnings: List[Dict[str, str]],
) -> None:
    """
    作用: 扫描 AI content 中疑似职称的中文词组，若不在词典中则记 warning

    策略:
        1. 提取 Markdown 标题行（## xxx）中的 2-5 字中文词组
        2. 在正文中搜索"职称"指示词附近的 2-5 字中文词组
        3. 过滤掉已知词典职称、已提取职称、常见非职称词
    """
    if not content:
        return

    # 常见非职称中文词组（避免误报）
    COMMON_NON_TITLE = {'研究方向', '个人简介', '教育背景', '工作经历', '学术兼职',
                        '基本信息', '联系方式', '办公电话', '电子邮箱', '课程名称',
                        '课程简介', '教学大纲', '上课时间', '基本信息', '论文标题'}

    # 中文词组正则（2-5个汉字）
    CN_WORD_PATTERN = re.compile(r'[\u4e00-\u9fa5]{2,5}')

    potential_titles: List[str] = []

    # 策略1：从标题行（## xxx）中提取疑似职称词
    for match in re.finditer(r'^#{1,3}\s+(.+)$', content, re.MULTILINE):
        heading = match.group(1).strip()
        # 尝试在标题中按空格/分隔符拆词
        for word in CN_WORD_PATTERN.findall(heading):
            if (word not in known_titles
                    and word not in already_extracted
                    and word not in potential_titles
                    and word not in COMMON_NON_TITLE):
                potential_titles.append(word)

    # 策略2：在"职称"或"职务"指示词附近寻找
    for indicator in ['职称', '职务', '头衔']:
        idx = content.find(indicator)
        if idx >= 0:
            nearby = content[idx:idx + 50]
            for word in CN_WORD_PATTERN.findall(nearby):
                if (word != indicator
                        and word not in known_titles
                        and word not in already_extracted
                        and word not in potential_titles
                        and word not in COMMON_NON_TITLE):
                    potential_titles.append(word)

    # 策略3：在类似「姓名 + 空格 + 头衔」的标题行中提取
    name_title_pattern = re.compile(
        r'^#{1,3}\s+[\u4e00-\u9fa5]{2,4}\s+([\u4e00-\u9fa5]{2,5})', re.MULTILINE
    )
    for match in name_title_pattern.finditer(content):
        candidate = match.group(1).strip()
        if (candidate not in known_titles
                and candidate not in already_extracted
                and candidate not in potential_titles
                and candidate not in COMMON_NON_TITLE):
            potential_titles.append(candidate)

    # 对每个疑似职称生成 warning
    for title in potential_titles:
        warnings.append({
            "field": "title",
            "message": f"职称 '{title}' 不在教育词典中，可能是AI推断的非标准表述",
        })


# ============================================================
# 页面类型推断
# ============================================================

def _detect_page_type(markdown: str) -> str:
    """
    作用: 根据关键词密度推断页面类型

    返回: 'teacher' / 'course' / 'research' / 'unknown'
    """
    if not markdown:
        return 'unknown'

    markdown_lower = markdown.lower()
    scores: Dict[str, int] = {}

    for ptype, keywords in PAGE_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in markdown_lower)
        scores[ptype] = score

    if not scores:
        return 'unknown'

    best_type = max(scores, key=scores.get)  # type: ignore
    if scores[best_type] >= 2:
        return best_type

    return 'unknown'


# ============================================================
# 各页面类型专项提取
# ============================================================

def _extract_teacher_info(
    markdown: str,
    emails: List[str],
    phones: List[str],
    titles: List[str],
) -> Tuple[Dict[str, str], str]:
    """
    作用: 从 Markdown 中提取教师信息

    返回: (extracted_dict, confidence)
    """
    extracted: Dict[str, str] = {}

    # 姓名
    name = _extract_name_from_markdown(markdown)
    extracted["name"] = name or ""

    # 职称
    extracted["title"] = titles[0] if titles else ""

    # 院系
    department = _extract_keyword_nearby(
        markdown, ["院系", "学院", "系", "部门", "单位", "所属"]
    )
    if not department:
        department = _extract_department(markdown)
    extracted["department"] = department or ""

    # 邮箱
    extracted["email"] = emails[0] if emails else ""

    # 电话
    extracted["phone"] = phones[0] if phones else ""

    # 研究方向
    research = _extract_keyword_nearby(
        markdown, ["研究方向", "研究领域", "研究兴趣", "科研方向"]
    )
    extracted["research"] = research or ""

    # 办公室
    office = _extract_keyword_nearby(
        markdown, ["办公室", "办公地点", "地址", "房间"]
    )
    extracted["office"] = office or ""

    # 个人简介（取较长段落）
    intro = _extract_keyword_nearby(
        markdown, ["个人简介", "简介", "个人介绍"], max_chars=500
    )
    extracted["introduction"] = intro or ""

    # 置信度评估
    filled = sum(1 for v in extracted.values() if v)
    if filled >= CONFIDENCE_HIGH_FIELDS:
        confidence = "high"
    elif filled >= CONFIDENCE_MEDIUM_FIELDS:
        confidence = "medium"
    else:
        confidence = "low"

    return extracted, confidence


def _extract_course_info(
    markdown: str,
    emails: List[str],
    phones: List[str],
) -> Tuple[Dict[str, str], str]:
    """
    作用: 从 Markdown 中提取课程信息
    """
    extracted: Dict[str, str] = {}

    # 课程名称
    name = _extract_name_from_markdown(markdown)
    extracted["course_name"] = name or ""

    # 授课教师
    teacher = _extract_keyword_nearby(
        markdown, ["授课教师", "任课教师", "主讲教师", "教师"]
    )
    extracted["teacher"] = teacher or ""

    # 学分
    credits = _extract_number_nearby(markdown, ["学分"])
    extracted["credits"] = str(credits) if credits is not None else ""

    # 学时
    hours = _extract_number_nearby(markdown, ["学时", "课时"])
    extracted["hours"] = str(hours) if hours is not None else ""

    # 课程简介
    syllabus = _extract_keyword_nearby(
        markdown, ["课程简介", "课程描述", "课程介绍", "内容简介"], max_chars=500
    )
    extracted["syllabus"] = syllabus or ""

    # 学期
    semester = _extract_keyword_nearby(markdown, ["学期", "开课学期", "学年"])
    extracted["semester"] = semester or ""

    # 邮箱和电话
    extracted["email"] = emails[0] if emails else ""
    extracted["phone"] = phones[0] if phones else ""

    # 置信度评估
    filled = sum(1 for v in extracted.values() if v)
    if filled >= CONFIDENCE_GENERIC_HIGH:
        confidence = "high"
    elif filled >= CONFIDENCE_GENERIC_MEDIUM:
        confidence = "medium"
    else:
        confidence = "low"

    return extracted, confidence


def _extract_research_info(markdown: str) -> Tuple[Dict[str, str], str]:
    """
    作用: 从 Markdown 中提取科研/论文信息
    """
    extracted: Dict[str, str] = {}

    # 论文标题
    title = _extract_name_from_markdown(markdown)
    extracted["paper_title"] = title or ""

    # 作者
    authors = _extract_keyword_nearby(markdown, ["作者", "作者信息", "作 者"])
    extracted["authors"] = authors or ""

    # 期刊
    journal = _extract_keyword_nearby(
        markdown, ["期刊", "发表", "杂志", "刊物", "出处"]
    )
    extracted["journal"] = journal or ""

    # 年份
    year_match = re.search(r'(?:19|20)\d{2}', markdown)
    extracted["year"] = str(year_match.group(0)) if year_match else ""

    # DOI
    doi_match = re.search(r'(?:doi|DOI)[：:：\s]*(10\.\d{4,}/[^\s]+)', markdown)
    extracted["doi"] = doi_match.group(1) if doi_match else ""

    # 置信度评估
    filled = sum(1 for v in extracted.values() if v)
    if filled >= CONFIDENCE_GENERIC_HIGH:
        confidence = "high"
    elif filled >= CONFIDENCE_GENERIC_MEDIUM:
        confidence = "medium"
    else:
        confidence = "low"

    return extracted, confidence


def _extract_generic_info(
    markdown: str,
    emails: List[str],
    phones: List[str],
    titles: List[str],
) -> Dict[str, str]:
    """
    作用: 无法判断页面类型时的通用提取（邮箱+电话+职称+标题）
    """
    extracted: Dict[str, str] = {}
    name = _extract_name_from_markdown(markdown)
    extracted["name"] = name or ""
    extracted["title"] = titles[0] if titles else ""
    extracted["email"] = emails[0] if emails else ""
    extracted["phone"] = phones[0] if phones else ""

    # 尝试提取院系
    department = _extract_department(markdown)
    extracted["department"] = department or ""

    return extracted


# ============================================================
# 内容组装与修正
# ============================================================

def _build_fallback_content(extracted: Dict[str, str], page_type: str) -> str:
    """
    作用: 将提取的字段字典组装为 Markdown 文本

    AI 不可用时规则提取的字段是确定性的，这里按页面类型组装为
    排版清晰、与 AI 输出风格一致的 Markdown，前端可直接渲染。
    """
    if not extracted:
        return "未能从页面中提取到有效信息。"

    lines = []

    if page_type == "teacher":
        # 标题行：姓名 + 职称
        name = extracted.get("name", "")
        title = extracted.get("title", "")
        header = name
        if title and title not in header:
            header = f"{name} {title}" if name else title
        if header.strip():
            lines.append(f"## {header.strip()}")
            lines.append("")

        # 基本信息
        has_basic = any(
            extracted.get(k) for k in ["department", "office"]
        )
        if has_basic:
            lines.append("**基本信息**")
            if extracted.get("department"):
                lines.append(f"- 院系: {extracted['department']}")
            if extracted.get("office"):
                lines.append(f"- 办公室: {extracted['office']}")
            lines.append("")

        # 联系方式
        has_contact = any(
            extracted.get(k) for k in ["email", "phone"]
        )
        if has_contact:
            lines.append("**联系方式**")
            if extracted.get("email"):
                lines.append(f"- 邮箱: {extracted['email']}")
            if extracted.get("phone"):
                lines.append(f"- 电话: {extracted['phone']}")
            lines.append("")

        # 研究方向
        if extracted.get("research"):
            lines.append("**研究方向**")
            lines.append(f"- {extracted['research']}")
            lines.append("")

        # 个人简介
        if extracted.get("introduction"):
            lines.append("**个人简介**")
            lines.append(extracted["introduction"])
            lines.append("")

    elif page_type == "course":
        name = extracted.get("course_name", "")
        if name:
            lines.append(f"## {name}")
            lines.append("")

        has_basic = any(
            extracted.get(k) for k in ["teacher", "credits", "hours", "semester"]
        )
        if has_basic:
            lines.append("**基本信息**")
            if extracted.get("teacher"):
                lines.append(f"- 授课教师: {extracted['teacher']}")
            if extracted.get("credits"):
                lines.append(f"- 学分: {extracted['credits']}")
            if extracted.get("hours"):
                lines.append(f"- 学时: {extracted['hours']}")
            if extracted.get("semester"):
                lines.append(f"- 开课学期: {extracted['semester']}")
            lines.append("")

        if extracted.get("email"):
            lines.append(f"- 联系邮箱: {extracted['email']}")
        if extracted.get("phone"):
            lines.append(f"- 联系电话: {extracted['phone']}")
        if extracted.get("email") or extracted.get("phone"):
            lines.append("")

        if extracted.get("syllabus"):
            lines.append("**课程简介**")
            lines.append(extracted["syllabus"])
            lines.append("")

    elif page_type == "research":
        title = extracted.get("paper_title", "")
        if title:
            lines.append(f"## {title}")
            lines.append("")

        if extracted.get("authors"):
            lines.append(f"- 作者: {extracted['authors']}")
        if extracted.get("journal"):
            lines.append(f"- 期刊: {extracted['journal']}")
        if extracted.get("year"):
            lines.append(f"- 年份: {extracted['year']}")
        if extracted.get("doi"):
            lines.append(f"- DOI: {extracted['doi']}")
        if any(extracted.get(k) for k in ["authors", "journal", "year", "doi"]):
            lines.append("")

    else:
        # 通用/未知类型
        name = extracted.get("name", "")
        title = extracted.get("title", "")
        header = name
        if title and title not in header:
            header = f"{name} {title}" if name else title
        if header.strip():
            lines.append(f"## {header.strip()}")
            lines.append("")

        if extracted.get("department"):
            lines.append(f"- 院系: {extracted['department']}")
        if extracted.get("email"):
            lines.append(f"- 邮箱: {extracted['email']}")
        if extracted.get("phone"):
            lines.append(f"- 电话: {extracted['phone']}")

    return "\n".join(lines).strip()


def _remove_invalid_field_from_markdown(
    content: str, field_label: str, invalid_value: str
) -> str:
    """
    作用: 从 Markdown 内容中删除包含无效值的字段行

    例如: "邮箱: badformat" → 删除整行
    """
    if not invalid_value or not content:
        return content

    lines = content.split('\n')
    result_lines = []
    for line in lines:
        # 检查该行是否包含 field_label 和 invalid_value
        if field_label in line and invalid_value in line:
            continue  # 跳过错行
        result_lines.append(line)

    return '\n'.join(result_lines)


def _insert_field_into_content(
    content: str, field_label: str, field_value: str
) -> str:
    """
    作用: 将缺失的字段插入 Markdown content 末尾

    例如: AI 遗漏了职称，补充 "\n- 职称: 教授" 到末尾
    """
    if not field_value or not content:
        return content

    # 检查是否已存在该字段
    if field_label in content:
        return content

    return f"{content}\n- {field_label}: {field_value}"
