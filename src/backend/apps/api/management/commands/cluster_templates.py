"""
文件名: cluster_templates.py
作用: Django 管理命令 —— 离线 DBSCAN 聚类，自动发现模板类型

当前状态：骨架预留。待数据库中有足够的 PageSnapshot 记录后启用。

主要功能（待实现）:
    1. 查询所有已完成转换的 PageSnapshot 记录
    2. 逐条计算 DOM simhash 指纹
    3. 使用 sklearn.cluster.DBSCAN 进行聚类
    4. 对每个簇输出代表性 URL（簇中心）
    5. 人工审查后，为各簇配置 CSS 选择器规则

使用方式（规划）:
    python manage.py cluster_templates --min-samples=10 --eps=6
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """DBSCAN 模板聚类 —— 自动发现页面模板类型"""
    help = '使用 DBSCAN 对页面 DOM 指纹聚类，自动发现模板（待数据充足后启用）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-samples',
            type=int,
            default=10,
            help='DBSCAN min_samples 参数（默认10）',
        )
        parser.add_argument(
            '--eps',
            type=int,
            default=6,
            help='DBSCAN eps 参数——海明距离阈值（默认6）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅输出聚类结果，不更新数据库',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'cluster_templates 命令当前为骨架占位，尚未实现。'
        ))
        self.stdout.write('待 PageSnapshot 表中积累足够已完成记录后启用。')
        self.stdout.write('')
        self.stdout.write(
            '预期流程：\n'
            '  1. 查询 process_status=completed 的记录\n'
            '  2. 逐条计算 DOM simhash 指纹\n'
            '  3. 用 DBSCAN 聚类（海明距离）\n'
            '  4. 输出各簇代表性 URL\n'
            '  5. 人工审查后配置 CSS 选择器规则'
        )
