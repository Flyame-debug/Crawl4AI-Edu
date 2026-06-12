"""
文件名: process_conversion.py
作用: Django 管理命令 —— 批量处理待转换的页面（HTML→Markdown）
主要功能:
    1. 查询 process_status 为 pending 或 failed 的 PageSnapshot 记录
    2. 每次最多处理 50 条，避免内存溢出
    3. 逐条调用 conversion.convert_page() 进行转换
    4. 输出处理进度和统计信息
"""

import logging
from django.core.management.base import BaseCommand
from apps.api.models import PageSnapshot
from apps.api.services.conversion import convert_page

logger = logging.getLogger('apps')


class Command(BaseCommand):
    """处理待转换页面：HTML → Markdown 转换"""
    help = '批量处理 pending/failed 状态的页面，执行 HTML→Markdown 转换'

    def add_arguments(self, parser):
        # 每次处理的最大记录数
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='每次处理的最大记录数（默认50）',
        )
        # 指定单个页面 ID 处理
        parser.add_argument(
            '--page-id',
            type=int,
            default=None,
            help='指定单个页面 ID 进行处理（调试用）',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        page_id = options['page_id']

        # 单页面处理模式（调试用）
        if page_id:
            self._process_single(page_id)
            return

        # 批量处理模式
        self._process_batch(batch_size)

    def _process_single(self, page_id: int) -> None:
        """
        作用: 处理指定 ID 的单条页面记录
        """
        self.stdout.write(f'处理单条页面: id={page_id}')
        result = convert_page(page_id)

        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ 转换成功: id={page_id}, url={result.get("url", "")}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ 转换失败: id={page_id}, '
                    f'错误: {result.get("error", "")}, '
                    f'重试次数: {result.get("retry_count", 0)}'
                )
            )

    def _process_batch(self, batch_size: int) -> None:
        """
        作用: 批量处理待转换页面
        """
        # 查询待处理记录（pending 正常处理 + failed 支持手动重试）
        pages = PageSnapshot.objects.filter(
            process_status__in=['pending', 'failed']
        ).exclude(
            raw_html=''
        ).order_by('?')[:batch_size]

        total = pages.count()

        if total == 0:
            self.stdout.write('没有待处理的页面')
            return

        self.stdout.write(f'开始批量处理，共 {total} 条待处理页面')

        success_count = 0
        fail_count = 0

        for i, page in enumerate(pages, 1):
            self.stdout.write(f'[{i}/{total}] 处理: {page.url} (id={page.id})')
            result = convert_page(page.id)

            if result['success']:
                success_count += 1
                stats = result.get('stats', {})
                self.stdout.write(
                    f'  ✓ 成功 | 原始: {stats.get("original_length", 0)} 字符 '
                    f'→ Markdown: {stats.get("markdown_length", 0)} 字符'
                )
            else:
                fail_count += 1
                self.stdout.write(
                    f'  ✗ 失败 | 错误: {result.get("error", "未知")[:100]}'
                )

        # 输出汇总统计
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f'批量处理完成: 成功 {success_count} 条, 失败 {fail_count} 条, '
                f'总计 {total} 条'
            )
        )
        self.stdout.write('=' * 50)
