"""
文件名: run_v2_migration.py
作用: 执行 V2.0 数据库迁移，为各表添加新字段
主要功能:
    1. 连接 PostgreSQL 数据库
    2. 为各表添加 V2.0 新增列
    3. 创建 user_template_history 表
"""
import psycopg2

# 数据库连接参数（请根据实际情况修改密码）
conn = psycopg2.connect(
    host='127.0.0.1',
    port=5432,
    database='crawl_db',
    user='postgres',
    password='123456',
)
cur = conn.cursor()

# ========== templates 表 ==========
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'other'")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS ai_model VARCHAR(100) DEFAULT 'qwen2:7b'")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS ai_api_url VARCHAR(200) DEFAULT 'http://127.0.0.1:11434'")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS ai_api_key VARCHAR(200) NULL")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS user_prompt TEXT NULL")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS created_by_id INTEGER NULL")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE")
cur.execute("ALTER TABLE templates ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'approved'")

# ========== crawl_tasks 表 ==========
cur.execute("ALTER TABLE crawl_tasks ADD COLUMN IF NOT EXISTS task_name VARCHAR(200) NULL")
cur.execute("ALTER TABLE crawl_tasks ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'formal'")
cur.execute("ALTER TABLE crawl_tasks ADD COLUMN IF NOT EXISTS generated_rule TEXT NULL")
cur.execute("ALTER TABLE crawl_tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMP NULL")
cur.execute("ALTER TABLE crawl_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP NULL")
cur.execute("ALTER TABLE crawl_tasks ADD COLUMN IF NOT EXISTS template_id INTEGER NULL")

# ========== page_snapshots 表 ==========
cur.execute("ALTER TABLE page_snapshots ADD COLUMN IF NOT EXISTS task_type VARCHAR(20) DEFAULT 'formal'")
cur.execute("ALTER TABLE page_snapshots ADD COLUMN IF NOT EXISTS user_prompt TEXT NULL")
cur.execute("ALTER TABLE page_snapshots ADD COLUMN IF NOT EXISTS error_info TEXT NULL")
cur.execute("ALTER TABLE page_snapshots ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1")
cur.execute("ALTER TABLE page_snapshots ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP NULL")
cur.execute("ALTER TABLE page_snapshots ADD COLUMN IF NOT EXISTS task_id VARCHAR(36) NULL")

# ========== seed_urls 表 ==========
cur.execute("ALTER TABLE seed_urls ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0")
cur.execute("ALTER TABLE seed_urls ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0")
cur.execute("ALTER TABLE seed_urls ADD COLUMN IF NOT EXISTS error_message TEXT NULL")
cur.execute("ALTER TABLE seed_urls ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL")

# ========== users 表 ==========
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR(200) NULL")
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL")

# ========== 新建 user_template_history 表 ==========
cur.execute("""
    CREATE TABLE IF NOT EXISTS user_template_history (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        template_id INTEGER NOT NULL,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, template_id)
    )
""")

conn.commit()
conn.close()
print('V2.0 数据库迁移完成！')
