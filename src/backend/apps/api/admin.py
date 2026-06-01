from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import PageSnapshot, SeedURL

@admin.register(PageSnapshot)
class PageSnapshotAdmin(admin.ModelAdmin):
    list_display = ['url', 'category', 'created_at']
    search_fields = ['url']

@admin.register(SeedURL)
class SeedURLAdmin(admin.ModelAdmin):
    list_display = ['url', 'school', 'status', 'need_render']
    search_fields = ['url', 'school']