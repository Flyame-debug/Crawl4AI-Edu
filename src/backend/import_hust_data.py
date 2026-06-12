# E:\Crawl4AI\src\backend\import_hust_data.py

import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_backend.settings')
django.setup()

from apps.api.models import PageSnapshot
from django.utils import timezone

# 修正：sandbox 不是 sandox
DATA_DIR = 'E:/Crawl4AI/data/hust_data/sandbox/data'
HTML_DIR = os.path.join(DATA_DIR, 'html')
IMAGES_DIR = os.path.join(DATA_DIR, 'images')
MAPPING_FILE = os.path.join(DATA_DIR, 'mapping.txt')
METADATA_FILE = os.path.join(DATA_DIR, 'metadata.json')

def import_data():
    # 1. 读取metadata.json
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # 2. 读取mapping.txt
    url_mapping = {}
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                url_mapping[key.strip()] = value.strip()
    
    # 3. 遍历HTML文件
    count = 0
    for filename in os.listdir(HTML_DIR):
        if filename.endswith('.html'):
            html_path = os.path.join(HTML_DIR, filename)
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            name_key = filename.replace('.html', '')
            teacher_info = metadata.get(name_key, {})
            original_url = url_mapping.get(name_key, '')
            
            PageSnapshot.objects.create(
                url=original_url or f'file://hust/{filename}',
                raw_html=html_content,
                markdown=html_content,
                extracted_data={
                    'name': teacher_info.get('name', ''),
                    'title': teacher_info.get('title', ''),
                    'research': teacher_info.get('research', ''),
                    'email': teacher_info.get('email', ''),
                },
                category='师资',
                page_type='teacher',
                process_status='pending',
                created_at=timezone.now()
            )
            count += 1
            print(f"✅ 导入: {filename} - {teacher_info.get('name', '未知')}")
    
    print(f"\n总计导入 {count} 条")

if __name__ == '__main__':
    import_data()