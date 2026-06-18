import os
import redis
from minio import Minio
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

def test_redis():
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            password=os.getenv('REDIS_PASSWORD') or None,  # 如果密码为空字符串则转为 None
            decode_responses=True,
            protocol=2   # 强制使用 RESP2 协议，兼容 Redis 5.x
        )
        r.ping()
        print("✅ Redis连接成功")
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")

def test_minio():
    try:
        client = Minio(
            os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            secure=os.getenv('MINIO_SECURE', 'False').lower() == 'true'
        )
        # 列出所有存储桶以验证连接
        buckets = client.list_buckets()
        print(f"✅ MinIO连接成功，当前有 {len(buckets)} 个存储桶")
    except Exception as e:
        print(f"❌ MinIO连接失败: {e}")

if __name__ == "__main__":
    test_redis()
    test_minio()