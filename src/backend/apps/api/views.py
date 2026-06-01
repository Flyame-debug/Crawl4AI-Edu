from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import PageSnapshot, SeedURL
from .serializers import PageSnapshotSerializer, SeedURLSerializer


class PageSnapshotViewSet(viewsets.ModelViewSet):
    """网页快照 API"""
    queryset = PageSnapshot.objects.all().order_by('-created_at')
    serializer_class = PageSnapshotSerializer
    
    def get_queryset(self):
        """支持按分类、关键词搜索"""
        queryset = super().get_queryset()
        
        # 按分类筛选
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 关键词搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(url__icontains=search) | Q(markdown__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def auto_category(self, request):
        """根据 URL 自动分类"""
        url = request.data.get('url')
        if not url:
            return Response({'error': 'url required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 简单规则：根据 URL 关键词分类
        if '/teacher/' in url or '/faculty/' in url:
            category = '师资'
        elif '/course/' in url or '/syllabus/' in url:
            category = '课程'
        elif '/research/' in url or '/paper/' in url:
            category = '科研'
        else:
            category = '其他'
        
        return Response({'category': category})


class SeedURLViewSet(viewsets.ModelViewSet):
    """种子URL API"""
    queryset = SeedURL.objects.all().order_by('-created_at')
    serializer_class = SeedURLSerializer
    
    def get_queryset(self):
        """支持按学校、状态筛选"""
        queryset = super().get_queryset()
        
        school = self.request.query_params.get('school')
        if school:
            queryset = queryset.filter(school=school)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def check_dead(self, request, pk=None):
        """检查死链"""
        import requests
        seed = self.get_object()
        
        try:
            resp = requests.head(seed.url, timeout=10, allow_redirects=True)
            if resp.status_code >= 400:
                seed.status = 'failed'
                seed.save()
                return Response({'status': 'dead', 'code': resp.status_code})
            return Response({'status': 'alive', 'code': resp.status_code})
        except Exception as e:
            seed.status = 'failed'
            seed.save()
            return Response({'status': 'dead', 'error': str(e)})