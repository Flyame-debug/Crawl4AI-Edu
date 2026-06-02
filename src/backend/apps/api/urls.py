from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pages', views.PageSnapshotViewSet, basename='page')
router.register(r'seeds', views.SeedURLViewSet, basename='seed')

urlpatterns = [
    path('', include(router.urls)),
]