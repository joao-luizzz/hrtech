"""
HRTech - URLs do App Core (Fase 3)
==================================

Rotas para upload e processamento de CVs.

Estrutura:
    /                   → home (página inicial)
    /upload/            → upload_cv (formulário)
    /upload/processar/  → processar_upload (POST, HTMX)
    /upload/status/<id> → status_cv_htmx (polling HTMX)
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Página inicial
    path('', views.home, name='home'),

    # Upload de CV
    path('upload/', views.upload_cv, name='upload_cv'),
    path('upload/processar/', views.processar_upload, name='processar_upload'),
    path('upload/status/<str:candidato_id>/', views.status_cv_htmx, name='status_cv_htmx'),
]
