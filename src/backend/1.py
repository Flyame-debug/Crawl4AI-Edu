#全量自测代码
from apps.api.models import *
from apps.api.services.snapshot_service import PageSnapshotService
from apps.api.utils import MinioClient,robot_checker
from django.conf import settings

#1.配置打印
print("===爬虫伦理配置===",settings.CRAWLER_ETHICS)
#2.服务测试
res=PageSnapshotService.save_or_update("https://test.edu.cn","测试正文内容")
print("===快照保存结果===",res)
#3.robots测试
print("===robots检测===",robot_checker.can_fetch("https://www.edu.cn"))
#4.统计数据预计算（和/api/stats逻辑一致）
from apps.stats.views import get_stats
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
req=APIRequestFactory().get("/")
print("===统计数据===",get_stats(req).data)