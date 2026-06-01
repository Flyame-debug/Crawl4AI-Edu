"""
功能：API 路由配置
用途：把 URL 地址映射到对应的视图函数
- /api/pages/ -> PageSnapshotViewSet
- /api/seeds/ -> SeedURLViewSet
调用方：被 edu_backend/urls.py 包含
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pages', views.PageSnapshotViewSet, basename='page')
router.register(r'seeds', views.SeedURLViewSet, basename='seed')

urlpatterns = [
    path('', include(router.urls)),
]