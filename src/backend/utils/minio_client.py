"""
功能：MinIO 图片存储工具
用途：上传图片到 MinIO 对象存储，返回访问 URL
调用方：成员 A（爬虫存图片时调用）
状态：备用，图片存储不是核心功能，可暂缓
"""

from minio import Minio
from django.conf import settings
import hashlib


class MinioClient:
    """MinIO 存储客户端"""
    
    def __init__(self):
        config = settings.MINIO_CONFIG
        self.client = Minio(
            config['endpoint'],
            access_key=config['access_key'],
            secret_key=config['secret_key'],
            secure=config['secure']
        )
        self.bucket = config['bucket_name']
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
    
    def upload_image(self, image_bytes: bytes, original_url: str = None) -> str:
        """上传图片，返回访问 URL"""
        filename = hashlib.md5(original_url.encode()).hexdigest()
        object_name = f"images/{filename}.jpg"
        self.client.put_object(
            self.bucket,
            object_name,
            image_bytes,
            len(image_bytes),
            content_type='image/jpeg'
        )
        return f"http://{settings.MINIO_CONFIG['endpoint']}/{self.bucket}/{object_name}"