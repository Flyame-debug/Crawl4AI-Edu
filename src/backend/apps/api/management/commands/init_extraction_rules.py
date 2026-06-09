"""
文件名: init_extraction_rules.py
作用: Django 管理命令 —— 在 Template 表中创建 3 套初始提取规则
主要功能:
    1. 为 teacher 类型创建默认 CSS 选择器规则
    2. 为 course 类型创建默认 CSS 选择器规则
    3. 为 research 类型创建默认 CSS 选择器规则
    4. 规则存储在 Template.config.extraction_rules 中
使用方式:
    python manage.py init_extraction_rules
"""

from django.core.management.base import BaseCommand
from apps.api.models import Template
from apps.api.services.extraction.rules import get_default_rules_config


class Command(BaseCommand):
    """初始化提取规则模板 —— 创建 teacher/course/research 三套默认规则"""
    help = '在 Template 表中创建初始提取规则（teacher/course/research）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制覆盖已存在的规则模板',
        )

    def handle(self, *args, **options):
        force = options['force']

        # 各类型模板的初始定义
        template_defs = [
            {
                'name': '教师页面通用规则',
                'page_type': 'teacher',
                'seed_url': 'https://example.edu/teacher',
                'description': '适用于中文高校教师个人主页的通用提取规则',
                'tags': ['教师', '师资', '通用'],
            },
            {
                'name': '课程页面通用规则',
                'page_type': 'course',
                'seed_url': 'https://example.edu/course',
                'description': '适用于中文高校课程介绍页面的通用提取规则',
                'tags': ['课程', '教学', '通用'],
            },
            {
                'name': '科研页面通用规则',
                'page_type': 'research',
                'seed_url': 'https://example.edu/research',
                'description': '适用于中文学术论文/科研成果页面的通用提取规则',
                'tags': ['科研', '论文', '通用'],
            },
        ]

        for tdef in template_defs:
            name = tdef['name']
            page_type = tdef['page_type']

            # 检查是否已存在同名模板
            existing = Template.objects.filter(name=name).first()
            if existing:
                if force:
                    self.stdout.write(
                        self.style.WARNING(f'覆盖已存在的模板: {name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'跳过已存在的模板: {name}（使用 --force 强制覆盖）')
                    )
                    continue

            # 获取默认规则配置
            rules_config = get_default_rules_config(page_type)
            config_data = {'extraction_rules': rules_config}

            if existing and force:
                # 更新现有记录
                existing.seed_url = tdef['seed_url']
                existing.description = tdef['description']
                existing.tags = tdef['tags']
                existing.config = config_data
                existing.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 已更新: {name}')
                )
            else:
                # 创建新记录
                Template.objects.create(
                    name=name,
                    seed_url=tdef['seed_url'],
                    description=tdef['description'],
                    tags=tdef['tags'],
                    config=config_data,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 已创建: {name}')
                )

            # 输出规则详情
            selectors = rules_config.get('selectors', {})
            self.stdout.write(f'    类型: {page_type}')
            self.stdout.write(f'    字段数: {len(selectors)}')
            for field, sel in selectors.items():
                self.stdout.write(f'      {field}: {sel[:80]}{"..." if len(sel) > 80 else ""}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('初始提取规则初始化完成'))
