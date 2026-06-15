"""
文件名: import_crawled_data.py
作用: Django 管理命令 —— 将成员A爬取的HTML文件批量导入 PageSnapshot 表，并上传图片到 MinIO
主要功能:
    1. 读取 sandbox/data/metadata.json 获取 URL→文件 映射
    2. 读取 HTML 文件内容写入 PageSnapshot.raw_html
    3. 上传图片到 MinIO，将 MinIO URL 写入 PageSnapshot.images
    4. 根据 depth 预填 page_type（depth=0→teacher, depth=1→unknown）
    5. 设置 process_status='pending'，交由 Celery 定时任务自动处理
    6. 支持去重（跳过已存在的 URL）、干运行、分批控制
使用方式:
    python manage.py import_crawled_data                    # 全量导入
    python manage.py import_crawled_data --limit=100        # 只导入前100条
    python manage.py import_crawled_data --skip-images      # 跳过图片上传
    python manage.py import_crawled_data --dry-run          # 干运行（只统计不写入）
"""

import io
import json
import logging
import os
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.api.models import PageSnapshot

logger = logging.getLogger('apps')


class Command(BaseCommand):
    """
    作用: 批量导入爬取数据到 PageSnapshot 表
    """
    help = '从 sandbox/data/metadata.json 批量导入爬取数据到 PageSnapshot 表'

    # MinIO 配置
    MINIO_BUCKET = 'crawl4ai'

    def add_arguments(self, parser):
        # 每批处理的记录数
        parser.add_argument(
            '--batch-size',
            type=int,
            default=200,
            help='每批入库的记录数（默认200）',
        )
        # 限制导入条数（调试用）
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='最多导入的记录数（调试用，默认全量导入）',
        )
        # 跳过图片上传
        parser.add_argument(
            '--skip-images',
            action='store_true',
            help='跳过图片上传到 MinIO，仅记录原始文件路径',
        )
        # 干运行模式（只统计不写入）
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='干运行模式：仅统计和校验，不实际写入数据库或上传图片',
        )
        # 仅导入 depth=0 的教师主页
        parser.add_argument(
            '--teacher-only',
            action='store_true',
            help='仅导入教师主页（depth=0），跳过子栏目页',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        skip_images = options['skip_images']
        dry_run = options['dry_run']
        teacher_only = options['teacher_only']

        # 定位 metadata.json 文件
        # metadata.json 中的路径（如 data\html\xxx.html）相对于 sandbox/ 目录
        project_root = Path(settings.BASE_DIR).parent.parent  # src/backend → 项目根
        metadata_path = project_root / 'sandbox' / 'data' / 'metadata.json'
        data_dir = project_root / 'sandbox'

        if not metadata_path.exists():
            self.stdout.write(
                self.style.ERROR(f'metadata.json 不存在: {metadata_path}')
            )
            return

        # 读取元数据
        self.stdout.write(f'读取索引文件: {metadata_path}')
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        total_entries = len(metadata)
        self.stdout.write(f'索引文件共 {total_entries} 条记录')

        # 过滤 depth
        if teacher_only:
            metadata = {
                url: info
                for url, info in metadata.items()
                if info.get('depth', -1) == 0
            }
            self.stdout.write(
                f'仅保留教师主页（depth=0），剩余 {len(metadata)} 条'
            )

        # 转为列表方便分批
        entries = list(metadata.items())
        if limit and limit < len(entries):
            entries = entries[:limit]
            self.stdout.write(f'限制导入前 {limit} 条')

        # 初始化 MinIO 客户端
        minio_client = None
        upload_cache = {}  # 已上传图片的缓存: {文件名: MinIO_URL}

        if not skip_images:
            minio_client = self._init_minio()
            if minio_client is None:
                self.stdout.write(
                    self.style.WARNING('MinIO 初始化失败，将跳过图片上传')
                )
                skip_images = True

        # 统计计数
        stats = {
            'total': len(entries),
            'created': 0,
            'skipped': 0,
            'image_uploaded': 0,
            'image_cached': 0,
            'image_failed': 0,
            'html_not_found': 0,
            'errors': 0,
        }

        start_time = time.time()

        # 分批处理
        for batch_start in range(0, len(entries), batch_size):
            batch = entries[batch_start:batch_start + batch_size]
            batch_snapshots = []

            for url, info in batch:
                html_rel_path = info.get('html', '')
                image_rel_paths = info.get('images', [])
                depth = info.get('depth', 0)

                # 检查 URL 是否已存在
                if not dry_run:
                    exists = PageSnapshot.objects.filter(url=url).exists()
                    if exists:
                        stats['skipped'] += 1
                        continue

                # 读取 HTML 文件
                html_path = data_dir / html_rel_path.replace('\\', os.sep)
                if not html_path.exists():
                    self.stdout.write(
                        self.style.WARNING(f'HTML 文件不存在: {html_path}')
                    )
                    stats['html_not_found'] += 1
                    continue

                try:
                    with open(html_path, 'r', encoding='utf-8') as f:
                        raw_html = f.read()
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'读取 HTML 失败: {html_path}, 错误: {e}')
                    )
                    stats['errors'] += 1
                    continue

                # 处理图片上传
                final_image_urls = []
                if not skip_images and minio_client and image_rel_paths:
                    for img_rel_path in image_rel_paths:
                        img_filename = Path(img_rel_path).name
                        if img_filename in upload_cache:
                            final_image_urls.append(upload_cache[img_filename])
                            stats['image_cached'] += 1
                        else:
                            img_path = data_dir / img_rel_path.replace('\\', os.sep)
                            if img_path.exists():
                                try:
                                    minio_url = self._upload_image(
                                        minio_client, img_path, img_filename
                                    )
                                    if minio_url:
                                        upload_cache[img_filename] = minio_url
                                        final_image_urls.append(minio_url)
                                        stats['image_uploaded'] += 1
                                    else:
                                        final_image_urls.append(str(img_rel_path))
                                        stats['image_failed'] += 1
                                except Exception as e:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f'图片上传失败: {img_filename}, 错误: {e}'
                                        )
                                    )
                                    final_image_urls.append(str(img_rel_path))
                                    stats['image_failed'] += 1
                            else:
                                final_image_urls.append(str(img_rel_path))
                elif skip_images:
                    # 不传图片时，保留原始相对路径
                    final_image_urls = list(image_rel_paths)

                # 根据 depth 预填 page_type
                if depth == 0:
                    page_type = 'teacher'
                else:
                    page_type = 'unknown'

                if dry_run:
                    stats['created'] += 1
                else:
                    snapshot = PageSnapshot(
                        url=url,
                        raw_html=raw_html,
                        images=final_image_urls,
                        page_type=page_type,
                        category='教师',
                        process_status='pending',
                    )
                    batch_snapshots.append(snapshot)
                    stats['created'] += 1

            # 批量写入数据库
            if batch_snapshots:
                try:
                    with transaction.atomic():
                        PageSnapshot.objects.bulk_create(
                            batch_snapshots,
                            batch_size=batch_size,
                            ignore_conflicts=False,
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'批量写入失败: {e}')
                    )
                    stats['errors'] += len(batch_snapshots)
                    stats['created'] -= len(batch_snapshots)

            # 输出进度
            processed = batch_start + len(batch)
            elapsed = time.time() - start_time
            self.stdout.write(
                f'进度: {min(processed, stats["total"])}/{stats["total"]} '
                f'| 新建: {stats["created"]} '
                f'| 跳过: {stats["skipped"]} '
                f'| 图片: ↑{stats["image_uploaded"]} '
                f'✓{stats["image_cached"]} '
                f'✗{stats["image_failed"]} '
                f'| 耗时: {elapsed:.1f}s'
            )

        # 输出汇总统计
        elapsed_total = time.time() - start_time
        self.stdout.write('')
        self.stdout.write('=' * 60)
        mode_label = '[干运行] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode_label}导入完成: '
                f'新建 {stats["created"]} 条, '
                f'跳过 {stats["skipped"]} 条, '
                f'HTML缺失 {stats["html_not_found"]} 条, '
                f'错误 {stats["errors"]} 条, '
                f'总计 {stats["total"]} 条'
            )
        )
        if not skip_images:
            self.stdout.write(
                f'图片: 上传 {stats["image_uploaded"]} 张, '
                f'缓存命中 {stats["image_cached"]} 张, '
                f'失败 {stats["image_failed"]} 张'
            )
        self.stdout.write(f'总耗时: {elapsed_total:.1f}s')
        self.stdout.write('=' * 60)

        # 后续处理提示
        if not dry_run and stats['created'] > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'已入库 {stats["created"]} 条记录（状态: pending），'
                    'Celery Beat 将在下一轮自动处理。'
                )
            )
            self.stdout.write(
                '手动触发处理: python manage.py process_conversion'
            )

    def _init_minio(self):
        """
        作用: 初始化 MinIO 客户端，使用 settings 中的散变量构造
        """
        try:
            from minio import Minio

            endpoint = getattr(settings, 'MINIO_ENDPOINT', '127.0.0.1:9000')
            access_key = getattr(settings, 'MINIO_ACCESS_KEY', 'minioadmin')
            secret_key = getattr(settings, 'MINIO_SECRET_KEY', 'minioadmin')
            secure = getattr(settings, 'MINIO_SECURE', False)

            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )

            # 确保 Bucket 存在
            if not client.bucket_exists(self.MINIO_BUCKET):
                client.make_bucket(self.MINIO_BUCKET)
                self.stdout.write(f'创建 MinIO Bucket: {self.MINIO_BUCKET}')

            self.stdout.write(
                f'MinIO 连接成功: {endpoint}/{self.MINIO_BUCKET}'
            )
            return client

        except ImportError:
            self.stdout.write(
                self.style.WARNING('minio 库未安装，跳过图片上传')
            )
            return None
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'MinIO 连接失败: {e}')
            )
            return None

    def _upload_image(self, client, image_path, filename):
        """
        作用: 上传单张图片到 MinIO，返回访问 URL
        """
        from minio.error import S3Error

        # 读取图片二进制数据
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
            image_size = len(image_bytes)

        if image_size == 0:
            return None

        # 根据扩展名确定 content_type
        ext = Path(filename).suffix.lower()
        content_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')

        # 使用文件名（去扩展名）作为 object_name
        stem = Path(filename).stem
        object_name = f'images/{stem}{ext}'

        try:
            # minio put_object 需要类文件对象（有 .read()），不能直接传 bytes
            data = io.BytesIO(image_bytes)
            client.put_object(
                self.MINIO_BUCKET,
                object_name,
                data,
                image_size,
                content_type=content_type,
            )

            # 构造访问 URL
            endpoint = getattr(settings, 'MINIO_ENDPOINT', '127.0.0.1:9000')
            return f'http://{endpoint}/{self.MINIO_BUCKET}/{object_name}'

        except S3Error as e:
            logger.error(f'MinIO 上传失败: {filename}, 错误: {e}')
            return None
