# apps/api/crawler_config.py (新建)
#从 CrawlerConfig 模型读取配置给爬虫使用
from .models import CrawlerConfig

def get_crawler_config_from_db():
    """从 CrawlerConfig 模型中读取配置，转换为 standalone_crawler 所需格式"""
    config = {
        'max_concurrent': 5,
        'request_delay': 1.0,
        'allowed_domains': [],
        'white_list_patterns': [],
        'enable_dead_check': False,
    }
    
    for key in config.keys():
        try:
            db_config = CrawlerConfig.objects.get(key=key, enabled=True)
            config[key] = db_config.value
        except CrawlerConfig.DoesNotExist:
            pass
    
    # 处理 concurrency 别名
    try:
        concurrency_conf = CrawlerConfig.objects.get(key='concurrency', enabled=True)
        config['max_concurrent'] = concurrency_conf.value
    except CrawlerConfig.DoesNotExist:
        pass
    
    return config