import sys
import asyncio
from pathlib import Path

# 添加 sandbox 路径
sys.path.insert(0, 'E:/Crawl4AI/sandbox')

# 正确导入
from fetcher.core import async_fetch
from standalone_crawler.crawl4ai_client import convert_with_crawl4ai

async def test():
    print("=" * 50)
    print("测试爬虫抓取和转换")
    print("=" * 50)
    
    # 1. 抓取
    print("\n🔄 抓取 https://example.com/ ...")
    try:
        html = await async_fetch("https://example.com/")
        print(f"✅ HTML长度: {len(html)}")
        print(f"前200字符: {html[:200]}")
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        return
    
    # 2. 转换
    print("\n🔄 转换 Markdown ...")
    try:
        md = await convert_with_crawl4ai(html)
        print(f"✅ Markdown长度: {len(md)}")
        print(f"前200字符: {md[:200]}")
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    asyncio.run(test())