"""
批量上传图片到MinIO
"""
import os
from minio import Minio

# MinIO配置
MINIO_ENDPOINT = '127.0.0.1:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin'
BUCKET_NAME = 'crawl4ai'

# 连接MinIO
client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# 确保bucket存在
if not client.bucket_exists(BUCKET_NAME):
    client.make_bucket(BUCKET_NAME)
    print(f"✅ 创建bucket: {BUCKET_NAME}")

# 图片目录
IMAGE_DIR = 'E:/Crawl4AI/data/hust_data/sandbox/data/images'

# 上传图片
count = 0
for filename in os.listdir(IMAGE_DIR):
    if filename.endswith(('.jpg', '.png', '.gif', '.svg')):
        file_path = os.path.join(IMAGE_DIR, filename)
        object_name = f'images/hust/{filename}'
        
        try:
            client.fput_object(
                BUCKET_NAME,
                object_name,
                file_path,
                content_type=f'image/{filename.split(".")[-1]}'
            )
            print(f"✅ 上传成功: {filename}")
            count += 1
        except Exception as e:
            print(f"❌ 上传失败: {filename} - {e}")

print(f"\n总计上传 {count} 张图片")
print(f"访问地址: http://{MINIO_ENDPOINT}/{BUCKET_NAME}/images/hust/")