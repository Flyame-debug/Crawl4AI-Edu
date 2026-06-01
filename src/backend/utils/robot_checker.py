"""
功能：robots.txt 合规检查工具
用途：爬取前检查网站是否允许爬虫访问
调用方：成员 A（爬虫开始前调用）
状态：备用，合规检查不是核心功能，可暂缓
"""

from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from functools import lru_cache


class RobotChecker:
    """robots.txt 检查器"""
    
    @lru_cache(maxsize=100)
    def get_parser(self, domain: str) -> RobotFileParser:
        rp = RobotFileParser()
        rp.set_url(f"https://{domain}/robots.txt")
        try:
            rp.read()
        except Exception:
            pass
        return rp
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        domain = urlparse(url).netloc
        rp = self.get_parser(domain)
        return rp.can_fetch(user_agent, url)


robot_checker = RobotChecker()