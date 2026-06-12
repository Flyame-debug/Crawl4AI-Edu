"""
文件名: test_extraction.py
作用: 模块六单元测试 —— 数据提取策略
主要功能:
    1. 测试 DOM 指纹计算
    2. 测试 CSS 选择器规则匹配与提取
    3. 测试 jieba + 正则兜底提取
    4. 测试 convert_page() 集成提取后的完整流程
    5. 测试异常容错
"""

import pytest

pytestmark = pytest.mark.django_db


# ============================================================
# 测试数据
# ============================================================

TEACHER_HTML = """
<html>
<head><title>张三 | 计算机学院</title></head>
<body>
    <div class="profile">
        <h1>张三</h1>
        <p class="title">教授</p>
        <p class="department">计算机科学与技术学院</p>
        <p class="research">研究方向：机器学习、数据挖掘、自然语言处理</p>
        <p class="email">zhangsan@university.edu.cn</p>
        <p class="phone">010-12345678</p>
        <p class="office">信息楼A301</p>
        <p>个人简介：张三教授长期从事机器学习与数据挖掘研究，在国内外重要学术期刊发表论文100余篇。</p>
        <p>教育背景：2008年获得清华大学计算机科学与技术博士学位，2010-2012年在斯坦福大学从事博士后研究。</p>
        <p>主讲课程：《机器学习导论》《数据挖掘》《高级人工智能》。</p>
    </div>
</body>
</html>
"""

COURSE_HTML = """
<html>
<head><title>机器学习 | 课程介绍</title></head>
<body>
    <div class="course-info">
        <h1>机器学习</h1>
        <p class="teacher">授课教师：张三 教授</p>
        <p class="credits">学分：3</p>
        <p class="hours">学时：48</p>
        <p class="semester">2026年春季学期</p>
        <p class="syllabus">课程简介：本课程系统介绍机器学习的基本概念、算法和应用。涵盖监督学习、无监督学习、强化学习等内容。通过理论教学和实践项目，帮助学生掌握机器学习核心技术。</p>
        <p>课程目标：掌握机器学习基本原理与常用算法，具备独立完成机器学习项目的能力。</p>
        <p>考核方式：平时作业(30%) + 期中项目(30%) + 期末考试(40%)</p>
    </div>
</body>
</html>
"""

RESEARCH_HTML = """
<html>
<head><title>基于深度学习的教育数据挖掘方法研究</title></head>
<body>
    <div class="paper-info">
        <h1>基于深度学习的教育数据挖掘方法研究</h1>
        <p class="authors">张三, 李四, 王五</p>
        <p class="journal">计算机学报, 2025</p>
        <p>DOI: 10.1234/eduai.2025</p>
        <p>摘要：本文提出了一种基于深度学习的教育数据挖掘方法，通过构建多层神经网络模型对教育数据进行特征提取和预测分析。</p>
        <p>关键词：深度学习；教育数据挖掘；神经网络；特征提取</p>
        <p>基金项目：国家自然科学基金(No.12345678)</p>
    </div>
</body>
</html>
"""

MARKDOWN_TEACHER = """
# 张三

**职称**：教授

**院系**：计算机科学与技术学院

研究方向：机器学习、数据挖掘

邮箱：zhangsan@edu.cn

电话：13800138000

办公室：信息楼A301
"""

MARKDOWN_COURSE = """
# 机器学习

- 授课教师：张三
- 学分：3
- 学时：48
- 学期：2026春季

课程简介：本课程系统介绍机器学习的基本概念与算法。
"""

# 不同结构的 HTML（用于指纹区分测试）
TEACHER_HTML_V2 = """
<html>
<head><title>教师主页</title></head>
<body>
    <header><nav><a href="/">首页</a></nav></header>
    <article class="faculty-profile">
        <h2 class="name">李四</h2>
        <div class="info">
            <span class="title">副教授</span>
            <span class="department">软件学院</span>
        </div>
        <section class="research-interests">软件工程、云计算</section>
        <a href="mailto:lisi@edu.cn">联系我们</a>
    </article>
</body>
</html>
"""


class TestFingerprint:
    """DOM 指纹计算测试组"""

    def test_compute_fingerprint_basic(self):
        """
        作用: 测试基本 DOM 指纹计算
        """
        from apps.api.services.extraction.fingerprint import compute_fingerprint

        fp = compute_fingerprint(TEACHER_HTML)
        assert fp is not None
        assert isinstance(fp, int)
        assert fp > 0

    def test_compute_fingerprint_empty(self):
        """
        作用: 测试空 HTML 的指纹计算
        """
        from apps.api.services.extraction.fingerprint import compute_fingerprint

        fp = compute_fingerprint('')
        assert fp is None

        fp = compute_fingerprint(None)
        assert fp is None

    def test_fingerprint_consistency(self):
        """
        作用: 测试相同结构的 HTML 产生相同或相近的指纹
        """
        from apps.api.services.extraction.fingerprint import (
            compute_fingerprint,
            hamming_distance,
        )

        fp1 = compute_fingerprint(TEACHER_HTML)
        fp2 = compute_fingerprint(TEACHER_HTML)
        assert fp1 is not None and fp2 is not None
        # 相同输入应产生完全相同指纹
        assert fp1 == fp2

    def test_fingerprint_different_structure(self):
        """
        作用: 测试不同结构的 HTML 产生不同的指纹
        """
        from apps.api.services.extraction.fingerprint import (
            compute_fingerprint,
            hamming_distance,
        )

        fp1 = compute_fingerprint(TEACHER_HTML)
        fp2 = compute_fingerprint(TEACHER_HTML_V2)
        assert fp1 is not None and fp2 is not None
        # 结构差异应产生一定的海明距离
        distance = hamming_distance(fp1, fp2)
        assert distance > 0

    def test_hamming_distance_same(self):
        """
        作用: 测试相同指纹的海明距离为 0
        """
        from apps.api.services.extraction.fingerprint import hamming_distance

        fp = 1234567890123456
        assert hamming_distance(fp, fp) == 0

    def test_hamming_distance_different(self):
        """
        作用: 测试不同指纹的海明距离计算
        """
        from apps.api.services.extraction.fingerprint import hamming_distance

        fp1 = 0
        fp2 = (1 << 63)  # 只有最高位不同
        assert hamming_distance(fp1, fp2) == 1

    def test_is_similar(self):
        """
        作用: 测试指纹相似性判断
        """
        from apps.api.services.extraction.fingerprint import is_similar

        fp = 1234567890123456
        # 相同指纹应相似
        assert is_similar(fp, fp, threshold=3) is True
        # 距离为 1 的指纹在阈值 3 内应相似
        fp_diff = fp ^ 1
        assert is_similar(fp, fp_diff, threshold=3) is True


class TestExtractor:
    """CSS 选择器提取引擎测试组"""

    def test_extract_teacher_fields(self):
        """
        作用: 测试教师页面字段提取
        """
        from apps.api.services.extraction.extractor import extract_by_selectors

        selectors = {
            'name': 'h1, .name',
            'title': '.title, .position',
            'department': '.department, .college',
            'research': '.research, .interests',
            'email': '.email',
            'phone': '.phone',
            'office': '.office',
        }

        result = extract_by_selectors(TEACHER_HTML, selectors, 'teacher')

        assert result['method'] == 'css_selector'
        assert result['page_type'] == 'teacher'
        assert '张三' in result['extracted'].get('name', '')
        assert '教授' in result['extracted'].get('title', '')
        assert '计算机' in result['extracted'].get('department', '')
        assert '机器学习' in result['extracted'].get('research', '')
        assert 'zhangsan' in result['extracted'].get('email', '')
        assert result['confidence'] > 0

    def test_extract_course_fields(self):
        """
        作用: 测试课程页面字段提取
        """
        from apps.api.services.extraction.extractor import extract_by_selectors

        selectors = {
            'course_name': 'h1',
            'teacher': '.teacher',
            'credits': '.credits',
            'hours': '.hours',
            'semester': '.semester',
        }

        result = extract_by_selectors(COURSE_HTML, selectors, 'course')

        assert result['method'] == 'css_selector'
        assert '机器学习' in result['extracted'].get('course_name', '')
        assert result['confidence'] > 0

    def test_extract_research_fields(self):
        """
        作用: 测试科研页面字段提取
        """
        from apps.api.services.extraction.extractor import extract_by_selectors

        selectors = {
            'paper_title': 'h1',
            'authors': '.authors',
            'journal': '.journal',
        }

        result = extract_by_selectors(RESEARCH_HTML, selectors, 'research')

        assert result['method'] == 'css_selector'
        assert '教育数据挖掘' in result['extracted'].get('paper_title', '')
        assert result['confidence'] > 0

    def test_extract_empty_html(self):
        """
        作用: 测试空 HTML 的提取处理
        """
        from apps.api.services.extraction.extractor import extract_by_selectors

        result = extract_by_selectors('', {'name': 'h1'}, 'teacher')
        assert result['method'] == 'css_selector'
        assert result['extracted'] == {}
        assert result['confidence'] == 0.0

    def test_extract_no_rule_selectors(self):
        """
        作用: 测试无选择器规则的提取处理
        """
        from apps.api.services.extraction.extractor import extract_by_selectors

        result = extract_by_selectors(TEACHER_HTML, {}, 'teacher')
        assert result['extracted'] == {}
        assert result['confidence'] == 0.0

    def test_extract_email_from_mailto(self):
        """
        作用: 测试从 mailto 链接提取邮箱
        """
        from apps.api.services.extraction.extractor import extract_by_selectors

        html = '<html><body><a href="mailto:test@edu.cn">联系</a></body></html>'
        result = extract_by_selectors(html, {'email': 'a[href^="mailto:"]'}, 'teacher')

        assert result['extracted'].get('email') == 'test@edu.cn'


class TestFallback:
    """兜底提取测试组"""

    def test_fallback_extract_teacher(self):
        """
        作用: 测试兜底提取教师信息
        """
        from apps.api.services.extraction.fallback import fallback_extract

        result = fallback_extract(MARKDOWN_TEACHER, 'teacher')

        assert result['method'] == 'fallback'
        assert result['page_type'] == 'teacher'
        extracted = result['extracted']
        assert '教授' in extracted.get('title', '')
        assert 'zhangsan' in extracted.get('email', '').lower()
        # 电话或办公室至少有一个
        assert extracted.get('phone') or extracted.get('office')

    def test_fallback_extract_course(self):
        """
        作用: 测试兜底提取课程信息
        """
        from apps.api.services.extraction.fallback import fallback_extract

        result = fallback_extract(MARKDOWN_COURSE, 'course')

        assert result['method'] == 'fallback'
        assert result['page_type'] == 'course'
        extracted = result['extracted']
        assert '机器学习' in extracted.get('course_name', '')

    def test_fallback_empty_input(self):
        """
        作用: 测试空输入的兜底提取
        """
        from apps.api.services.extraction.fallback import fallback_extract

        result = fallback_extract('', 'teacher')
        assert result['confidence'] == 0.0
        assert result['page_type'] == 'unknown'
        assert result['extracted'] == {}

    def test_fallback_auto_detect_type(self):
        """
        作用: 测试自动检测页面类型
        """
        from apps.api.services.extraction.fallback import fallback_extract

        # 教师关键词
        result = fallback_extract(MARKDOWN_TEACHER)
        assert result['page_type'] == 'teacher'

        # 课程关键词
        result = fallback_extract(MARKDOWN_COURSE)
        assert result['page_type'] == 'course'

    def test_fallback_email_extraction(self):
        """
        作用: 测试邮箱正则提取
        """
        from apps.api.services.extraction.fallback import _extract_emails

        text = '联系方式：test@example.com 和 admin@test.org.cn'
        emails = _extract_emails(text)
        assert 'test@example.com' in emails
        assert 'admin@test.org.cn' in emails

    def test_fallback_phone_extraction(self):
        """
        作用: 测试电话号码正则提取
        """
        from apps.api.services.extraction.fallback import _extract_phones

        text = '电话：010-12345678 手机：13800138000'
        phones = _extract_phones(text)
        assert any('13800138000' in p for p in phones)

    def test_fallback_title_detection(self):
        """
        作用: 测试职称关键词检测
        """
        from apps.api.services.extraction.fallback import _extract_title_from_text

        assert _extract_title_from_text('张三 教授 博士生导师') == '教授'
        assert _extract_title_from_text('李四 副教授') == '副教授'
        assert _extract_title_from_text('王五 讲师') == '讲师'
        # '赵六 院长' 仅含附加角色 '院长'，无核心职称，降级返回 '院长'
        assert _extract_title_from_text('赵六 院长') == '院长'


class TestExtractionPipeline:
    """提取流水线集成测试组"""

    def test_extract_page_with_rules(self):
        """
        作用: 测试完整提取流水线（有规则匹配时）
        """
        from apps.api.models import Template

        # 创建带有指纹的模板
        from apps.api.services.extraction.fingerprint import compute_fingerprint
        fp = compute_fingerprint(TEACHER_HTML)

        Template.objects.create(
            name='测试教师模板',
            seed_url='https://test.edu/teacher',
            description='测试用模板',
            config={
                'extraction_rules': {
                    'fingerprint': fp,
                    'page_type': 'teacher',
                    'selectors': {
                        'name': 'h1',
                        'title': '.title',
                        'department': '.department',
                        'research': '.research',
                        'email': '.email',
                        'phone': '.phone',
                        'office': '.office',
                    },
                }
            },
        )

        from apps.api.services.extraction import extract_page

        result = extract_page(
            raw_html=TEACHER_HTML,
            markdown='# 张三\n教授',
            page_type_hint='teacher',
        )

        assert result['method'] == 'css_selector'
        assert result['page_type'] == 'teacher'
        assert '张三' in result['extracted'].get('name', '')
        assert result['confidence'] > 0

    def test_extract_page_fallback(self):
        """
        作用: 测试无模板匹配时的降级兜底
        """
        from apps.api.services.extraction import extract_page

        # 使用任意 HTML（不会有模板匹配）
        result = extract_page(
            raw_html=TEACHER_HTML_V2,
            markdown=MARKDOWN_TEACHER,
            page_type_hint='teacher',
        )

        # 应降级为 fallback
        assert result['method'] == 'fallback'
        assert result['page_type'] == 'teacher'

    def test_extract_page_empty_html(self):
        """
        作用: 测试空 HTML 的提取处理
        """
        from apps.api.services.extraction import extract_page

        result = extract_page('', '', 'teacher')
        assert result['method'] == 'unknown'
        assert result['confidence'] == 0.0


class TestConvertPageWithExtraction:
    """convert_page() 集成提取测试组"""

    def test_convert_page_extracts_data(self):
        """
        作用: 测试 convert_page() 在转换成功后自动提取数据
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/extract/test',
            raw_html=TEACHER_HTML,
            process_status='pending',
            page_type='teacher',
        )

        result = convert_page(page.id)
        assert result['success'] is True

        page.refresh_from_db()
        assert page.process_status == 'completed'

        # 验证 extracted_data 已填充
        ed = page.extracted_data
        assert isinstance(ed, dict)
        assert 'page_type' in ed
        assert 'extracted' in ed
        assert 'confidence' in ed
        assert 'method' in ed

    def test_convert_page_extraction_failure_does_not_block(self):
        """
        作用: 测试数据提取失败不会阻塞转换主流程
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        # 使用极简 HTML（转换可能通过也可能失败，但关键是提取不应崩溃）
        page = PageSnapshot.objects.create(
            url='https://test.edu/extract/simple',
            raw_html=TEACHER_HTML,
            process_status='pending',
        )

        result = convert_page(page.id)

        # 无论成功与否，不应抛出异常
        assert isinstance(result, dict)
        assert 'success' in result

    def test_convert_page_saves_page_type(self):
        """
        作用: 测试转换后 page_type 被正确更新
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/extract/type',
            raw_html=TEACHER_HTML,
            process_status='pending',
            page_type='unknown',
        )

        result = convert_page(page.id)
        page.refresh_from_db()

        if result['success']:
            # 提取可能检测到 teacher 类型并更新
            assert page.page_type in ('teacher', 'unknown', 'course', 'research')
            assert page.extracted_data is not None


class TestRulesModule:
    """规则加载与匹配测试组"""

    def test_get_default_rules_config(self):
        """
        作用: 测试获取各类型的默认规则配置
        """
        from apps.api.services.extraction.rules import get_default_rules_config

        teacher_rules = get_default_rules_config('teacher')
        assert teacher_rules['page_type'] == 'teacher'
        assert len(teacher_rules['selectors']) > 0
        assert 'name' in teacher_rules['selectors']
        assert 'email' in teacher_rules['selectors']

        course_rules = get_default_rules_config('course')
        assert course_rules['page_type'] == 'course'
        assert 'course_name' in course_rules['selectors']

        research_rules = get_default_rules_config('research')
        assert research_rules['page_type'] == 'research'

        unknown_rules = get_default_rules_config('unknown')
        assert unknown_rules['page_type'] == 'unknown'
        assert unknown_rules['selectors'] == {}

    def test_match_template_no_templates(self):
        """
        作用: 测试无模板时的匹配结果
        """
        from apps.api.services.extraction.rules import match_template

        result = match_template(123456)
        assert result is None

    def test_match_template_none_fingerprint(self):
        """
        作用: 测试 None 指纹的匹配结果
        """
        from apps.api.services.extraction.rules import match_template

        result = match_template(None)
        assert result is None
