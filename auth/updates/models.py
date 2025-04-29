# app/updates/models.py

from django.db import models

class Release(models.Model):
    version       = models.CharField(max_length=50)
    changelog     = models.TextField(blank=True)
    file          = models.FileField(upload_to='updates/')  # armazena o .exe em MEDIA_ROOT/updates/
    published_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'published_at'
        ordering     = ['-published_at']

    def __str__(self):
        return f"v{self.version}"
