from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("<h1>🚀 后端框架已启动成功！</h1>")

urlpatterns = [
    path("", home),  # 根路径欢迎页
    path("admin/", admin.site.urls),
    path("api/", include("apps.api.urls")),
]
