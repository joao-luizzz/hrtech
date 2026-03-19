"""
HRTech - URLs Principais
========================

Rotas do projeto HRTech ATS.

Estrutura:
    /admin/     → Django Admin
    /           → App Core (upload de CVs)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

# Serve arquivos de media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
