# app/updates/admin.py
from django.contrib import admin
from .models import Release

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ('version','published_at')
