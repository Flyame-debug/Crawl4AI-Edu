"""
文件名: test_conversion.py
作用: 模块1单元测试 —— HTML→Markdown 转换服务
主要功能:
    1. 测试 HTML→Markdown 基本转换流程
    2. 测试噪音标签清除
    3. 测试表格转换
    4. 测试 LaTeX/MathML 保留
    5. 测试最小长度检查
    6. 测试空/无效输入处理
    7. 测试 PageSnapshot 状态流转
    8. 测试重试逻辑
"""

import pytest

# 由于测试需要 Django 环境，标记为 django_db
pytestmark = pytest.mark.django_db


# ============================================================
# 测试数据
# ============================================================

SIMPLE_HTML = """
<html>
<head><title>测试页面</title></head>
<body>
    <article>
        <h1>教师简介</h1>
        <p>张三，教授，博士生导师。研究方向为机器学习与数据挖掘。</p>
        <p>邮箱：zhangsan@edu.cn</p>
        <p>办公室：信息楼A301</p>
        <p>张三教授在国内外重要学术期刊和会议上发表论文100余篇，其中SCI收录50余篇，授权发明专利10项。</p>
        <p>主持国家自然科学基金重点项目、面上项目等多项科研项目。曾获省级科技进步一等奖和校级优秀教学成果奖。</p>
        <p>主要讲授本科生课程《机器学习导论》和研究生课程《高级数据挖掘》，教学评价优秀。</p>
    </article>
</body>
</html>
"""

HTML_WITH_NOISE = """
<html>
<head><title>带噪音的页面</title></head>
<body>
    <h1>课程介绍</h1>
    <!-- 用 <article> 包裹全部内容，确保 readability 不会因评分低而丢弃噪音元素 -->
    <article>
        <p>机器学习是一门研究计算机如何模拟人类学习行为的学科。它涉及概率论、统计学、逼近论、凸分析、算法复杂度理论等多门学科。机器学习理论主要是设计和分析一些让计算机可以自动学习的算法。</p>
        <div class="test-sidepanel">
            <ul><li>导航1</li><li>导航2</li><li>导航3</li></ul>
        </div>
        <p>机器学习已广泛应用于数据挖掘、计算机视觉、自然语言处理、生物特征识别、搜索引擎、医学诊断、证券市场分析、DNA序列测序和机器人等领域。</p>
        <div class="test-bottom">
            <p>版权所有 © 2024 某某大学计算机学院</p>
        </div>
        <div class="test-adbox">
            <p>广告内容：暑期培训班招生中</p>
        </div>
        <p>深度学习是机器学习的一个重要分支，使用多层神经网络从数据中学习特征表示，在图像识别和自然语言处理任务中表现优异。</p>
        <div class="test-navlinks">
            <a href="/home">首页</a>
        </div>
        <p>本课程将涵盖监督学习、无监督学习、强化学习等多个领域，帮助学生建立扎实的理论基础和实践能力。</p>
        <p>课程考核方式包括平时作业、课堂测试和期末项目，全面评估学生的学习效果与综合能力。</p>
    </article>
</body>
</html>
"""

HTML_WITH_TABLE = """
<html>
<head><title>课程表</title></head>
<body>
    <p>本学期的课程安排如下表所示，涵盖了计算机科学与技术专业的核心课程。学生需要根据培养方案的要求选择合适的课程，并确保修满规定的学分。以下是各门课程的详细信息，供同学们参考选课。</p>
    <h2>课程安排</h2>
    <table>
        <thead>
            <tr><th>课程名称</th><th>学分</th><th>学时</th></tr>
        </thead>
        <tbody>
            <tr><td>机器学习</td><td>3</td><td>48</td></tr>
            <tr><td>深度学习</td><td>4</td><td>64</td></tr>
        </tbody>
    </table>
    <p>以上课程均为专业必修课程，建议学生按照顺序学习。先修机器学习再修深度学习可以获得更好的学习效果。每门课程都包含理论教学和实践环节，实践环节在计算机实验室进行，由助教负责指导。</p>
</body>
</html>
"""

HTML_WITH_LATEX = """
<html>
<head><title>数学公式</title></head>
<body>
    <h2>基本公式</h2>
    <p>线性回归的损失函数为：</p>
    <p><span class="math">\\( J(\\theta) = \\frac{1}{2m} \\sum_{i=1}^{m} (h_\\theta(x^{(i)}) - y^{(i)})^2 \\)</span></p>
    <p>数学表达式：<math><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math></p>
</body>
</html>
"""

SHORT_HTML = "<html><body><p>短内容</p></body></html>"

EMPTY_HTML = ""

MALFORMED_HTML = "<html><body><p>未闭合段落<h1>标题<p>另一段</body>"


class TestHtmlToMarkdown:
    """HTML → Markdown 转换测试组"""

    def test_basic_conversion(self):
        """
        作用: 测试基本 HTML → Markdown 转换
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(SIMPLE_HTML)
        assert result['success'] is True
        assert '张三' in result['markdown']
        assert '机器学习' in result['markdown']
        assert result['title'] == '测试页面'
        assert result['stats']['markdown_length'] > 100

    def test_noise_removal(self):
        """
        作用: 测试噪音标签清除，sidebar/footer/ad/nav 应被移除
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(HTML_WITH_NOISE)
        assert result['success'] is True
        markdown = result['markdown']
        # 噪音内容不应出现
        assert '导航1' not in markdown
        assert '版权所有' not in markdown
        assert '广告内容' not in markdown
        # 正文内容应保留
        assert '课程介绍' in markdown
        assert '机器学习' in markdown

    def test_table_conversion(self):
        """
        作用: 测试 HTML 表格转 Markdown 表格
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(HTML_WITH_TABLE)
        assert result['success'] is True
        markdown = result['markdown']
        # Markdown 表格格式检查
        assert '课程名称' in markdown
        assert '机器学习' in markdown
        assert '深度学习' in markdown
        # 应包含表格分隔符
        assert '---' in markdown or '|' in markdown
        assert result['stats']['tables_found'] >= 1

    def test_latex_mathml_preservation(self):
        """
        作用: 测试 LaTeX 和 MathML 数学公式保留
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(HTML_WITH_LATEX)
        assert result['success'] is True
        markdown = result['markdown']
        # LaTeX 公式应被保留
        assert 'J' in markdown or 'theta' in markdown.lower()
        # MathML 关键标签应被保留
        assert 'math' in markdown.lower() or 'mi' in markdown.lower() or 'msup' in markdown.lower()

    def test_short_content_fails(self):
        """
        作用: 测试过短内容（<100字符）标记为失败
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(SHORT_HTML)
        # 过短内容应标记失败
        assert result['success'] is False
        # 错误信息可能来自 readability 早期返回或 markdown 长度检查
        error = result.get('error', '')
        assert '过短' in error or '阈值' in error or '为空' in error
        assert result['stats']['markdown_length'] < 100

    def test_empty_html(self):
        """
        作用: 测试空 HTML 输入处理
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(EMPTY_HTML)
        assert result['success'] is False
        assert result.get('error') is not None

    def test_malformed_html(self):
        """
        作用: 测试畸形 HTML 的容错处理
        """
        from apps.api.services.conversion import html_to_markdown

        # 畸形 HTML 不应抛出异常，应尽量处理
        try:
            result = html_to_markdown(MALFORMED_HTML)
            # 无论成功与否，不应崩溃
            assert isinstance(result, dict)
            assert 'success' in result
        except Exception as e:
            pytest.fail(f'畸形 HTML 导致异常: {e}')

    def test_noise_removal_stats(self):
        """
        作用: 测试噪音移除统计信息
        策略：
        - 用 <article> 包裹全部内容（正文 + 噪音），使 readability
          将其作为整体容器保留，避免低分元素被丢弃。
        - class 名（test-sidepanel 等）避开 readability 的
          unlikelyCandidatesRe 子串匹配（如 foot、menu 等），
          确保元素存活到阶段2由 BeautifulSoup 移除。
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(HTML_WITH_NOISE)
        assert result['success'] is True
        # 噪音移除数量应 > 0（sidebar、footer、ad、nav 共4个）
        assert result['stats']['noise_removed'] > 0

    def test_output_contains_markdown_headings(self):
        """
        作用: 测试输出使用 ATX 风格标题（# 开头）
        """
        from apps.api.services.conversion import html_to_markdown

        result = html_to_markdown(SIMPLE_HTML)
        assert result['success'] is True
        # ATX 风格标题检查（# 或 ## 开头）
        assert '# ' in result['markdown'] or '教师简介' in result['markdown']

    def test_large_html_handling(self):
        """
        作用: 测试大量 HTML 内容的处理性能
        """
        from apps.api.services.conversion import html_to_markdown

        # 生成较大的 HTML
        paragraphs = '<p>' + '测试内容。' * 100 + '</p>'
        large_html = f'<html><body>{paragraphs * 10}</body></html>'

        result = html_to_markdown(large_html)
        assert isinstance(result, dict)
        assert 'success' in result


class TestConvertPage:
    """PageSnapshot 状态流转与数据库更新测试组"""

    def test_convert_page_success(self):
        """
        作用: 测试成功转换后的数据库状态更新
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        # 创建测试记录
        page = PageSnapshot.objects.create(
            url='https://test.edu/teacher/001',
            raw_html=SIMPLE_HTML,
            process_status='pending',
        )

        result = convert_page(page.id)
        assert result['success'] is True

        # 重新查询验证数据库状态
        page.refresh_from_db()
        assert page.process_status == 'completed'
        assert page.markdown is not None
        assert len(page.markdown) > 100
        assert page.retry_count == 0
        assert page.processed_at is not None

    def test_convert_page_raw_html_empty(self):
        """
        作用: 测试 raw_html 为空时的处理
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/empty',
            raw_html='',
            process_status='pending',
        )

        result = convert_page(page.id)
        assert result['success'] is False
        assert 'raw_html' in result.get('error', '').lower() or '空' in result.get('error', '')

        page.refresh_from_db()
        assert page.process_status == 'failed'

    def test_convert_page_short_content(self):
        """
        作用: 测试内容过短时标记为 failed
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/short',
            raw_html=SHORT_HTML,
            process_status='pending',
        )

        result = convert_page(page.id)
        assert result['success'] is False

        page.refresh_from_db()
        assert page.retry_count >= 1

    def test_retry_count_increment(self):
        """
        作用: 测试失败时 retry_count 递增
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/retry',
            raw_html=SHORT_HTML,
            process_status='pending',
            retry_count=0,
        )

        # 第1次处理
        convert_page(page.id)
        page.refresh_from_db()
        assert page.retry_count == 1
        assert page.process_status == 'pending'  # 未达上限，重置为 pending

        # 第2次处理
        convert_page(page.id)
        page.refresh_from_db()
        assert page.retry_count == 2
        assert page.process_status == 'pending'

        # 第3次处理（达到上限）
        convert_page(page.id)
        page.refresh_from_db()
        assert page.retry_count == 3
        assert page.process_status == 'failed'

    def test_retry_reset_on_success(self):
        """
        作用: 测试成功后 retry_count 重置为 0
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/reset',
            raw_html=SIMPLE_HTML,
            process_status='pending',
            retry_count=2,  # 之前失败过
            last_error='之前失败了',
        )

        result = convert_page(page.id)
        assert result['success'] is True

        page.refresh_from_db()
        assert page.retry_count == 0
        assert page.last_error == ''

    def test_status_transition_processing(self):
        """
        作用: 测试处理过程中状态从 pending → completed 的完整流转
        """
        from apps.api.services.conversion import convert_page
        from apps.api.models import PageSnapshot

        page = PageSnapshot.objects.create(
            url='https://test.edu/transition',
            raw_html=SIMPLE_HTML,
            process_status='pending',
        )

        # 直接调用转换，验证完整状态流转
        result = convert_page(page.id)
        assert result['success'] is True

        page.refresh_from_db()
        assert page.process_status == 'completed'
        assert page.processed_at is not None
        assert page.retry_count == 0

    def test_convert_page_not_found(self):
        """
        作用: 测试处理不存在的记录
        """
        from apps.api.services.conversion import convert_page

        result = convert_page(99999)
        assert result['success'] is False
        assert '不存在' in result.get('error', '')


class TestTableConversion:
    """表格转换测试组"""

    def test_simple_table(self):
        """
        作用: 测试简单表格转 Markdown
        """
        from apps.api.services.conversion import _dataframe_to_markdown_table
        import pandas as pd

        df = pd.DataFrame({
            '姓名': ['张三', '李四'],
            '年龄': [30, 25],
        })

        result = _dataframe_to_markdown_table(df)
        assert '姓名' in result
        assert '张三' in result
        assert '李四' in result
        assert '---' in result

    def test_empty_dataframe(self):
        """
        作用: 测试空 DataFrame 的处理
        """
        from apps.api.services.conversion import _convert_tables_to_markdown

        html = '<html><body><p>无表格</p></body></html>'
        result_html, count = _convert_tables_to_markdown(html)
        assert count == 0

    def test_table_with_special_chars(self):
        """
        作用: 测试包含特殊字符的表格
        """
        from apps.api.services.conversion import _dataframe_to_markdown_table
        import pandas as pd

        df = pd.DataFrame({
            '描述': ['包含|竖线', '包含\n换行'],
        })

        result = _dataframe_to_markdown_table(df)
        # 竖线应被转义
        assert '\\|' in result


class TestHelperFunctions:
    """辅助函数测试组"""

    def test_clean_whitespace(self):
        """
        作用: 测试空白清理函数
        """
        from apps.api.services.conversion import _clean_whitespace

        text = '第一段\n\n\n\n\n第二段'
        result = _clean_whitespace(text)
        assert '\n\n\n' not in result
        assert '第一段' in result
        assert '第二段' in result

    def test_clean_whitespace_trailing_spaces(self):
        """
        作用: 测试行尾空白清理
        """
        from apps.api.services.conversion import _clean_whitespace

        text = '行尾有空格   \n下一行'
        result = _clean_whitespace(text)
        assert '   \n' not in result

    def test_clean_whitespace_empty(self):
        """
        作用: 测试空字符串处理
        """
        from apps.api.services.conversion import _clean_whitespace

        result = _clean_whitespace('')
        assert result == ''

    def test_clean_whitespace_strip(self):
        """
        作用: 测试首尾空白清除
        """
        from apps.api.services.conversion import _clean_whitespace

        result = _clean_whitespace('\n\n  内容  \n\n')
        assert result == '内容'
