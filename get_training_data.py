"""
获取教育类测试数据
用于成员B开发和测试提取规则
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

# 教育类测试种子（请替换为真实可用的URL）
EDU_SEEDS = [
    # 注意：请使用公开、允许爬取的URL
    # 示例：部分高校的公开教师页面
    {'url': 'https://www.cs.tsinghua.edu.cn/szjs/js.htm', 'school': '清华大学', 'category': '师资'},
    {'url': 'https://eecs.pku.edu.cn/szdw/yjs.htm', 'school': '北京大学', 'category': '师资'},
    {'url': 'https://www.zju.edu.cn/xxgk/teacher/', 'school': '浙江大学', 'category': '师资'},
]

def add_seeds():
    """添加教育类种子"""
    for seed in EDU_SEEDS:
        try:
            r = requests.post(f"{BASE_URL}/api/seedurl/", json=seed, timeout=10)
            print(f"添加: {seed['url']} - {r.status_code}")
        except Exception as e:
            print(f"添加失败: {seed['url']} - {e}")

def start_crawl():
    """启动爬虫"""
    for seed in EDU_SEEDS:
        try:
            r = requests.post(f"{BASE_URL}/api/crawl/start/", 
                              json={'seed_url': seed['url'], 'max_depth': 1})
            print(f"启动: {seed['url']} - 任务ID: {r.json().get('task_id')}")
        except Exception as e:
            print(f"启动失败: {seed['url']} - {e}")

def check_data():
    """查看数据量"""
    r = requests.get(f"{BASE_URL}/stats/")
    stats = r.json()
    print(f"\n当前数据统计:")
    print(f"  总页面数: {stats['total_pages']}")
    print(f"  分类统计: {stats['by_category']}")

def export_for_b():
    """导出数据供成员B使用"""
    r = requests.get(f"{BASE_URL}/api/pagesnapshot/?page_size=200")
    data = r.json()
    
    # 按分类导出
    pages = data.get('results', [])
    teacher_pages = [p for p in pages if p.get('category') == '师资']
    course_pages = [p for p in pages if p.get('category') == '课程']
    research_pages = [p for p in pages if p.get('category') == '科研']
    
    print(f"\n导出结果:")
    print(f"  教师页面: {len(teacher_pages)}")
    print(f"  课程页面: {len(course_pages)}")
    print(f"  科研页面: {len(research_pages)}")
    
    with open('teacher_pages.json', 'w', encoding='utf-8') as f:
        json.dump(teacher_pages, f, ensure_ascii=False, indent=2)
    
    with open('course_pages.json', 'w', encoding='utf-8') as f:
        json.dump(course_pages, f, ensure_ascii=False, indent=2)
    
    print("\n已导出: teacher_pages.json, course_pages.json")

if __name__ == "__main__":
    print("=" * 50)
    print("教育数据获取工具")
    print("=" * 50)
    
    add_seeds()
    print("\n等待5秒后启动爬虫...")
    time.sleep(5)
    
    start_crawl()
    print("\n等待30秒让爬虫运行...")
    time.sleep(30)
    
    check_data()
    export_for_b()