"""
HRTech - URLs do App Core (Fase 3 + Fase 4)
===========================================

Fase 3: Upload e processamento de CVs
Fase 4: Dashboards (RH, Candidato, Geral)

Estrutura:
    /                           → home (página inicial)
    /upload/                    → upload_cv (formulário)
    /upload/processar/          → processar_upload (POST, HTMX)
    /upload/status/<id>         → status_cv_htmx (polling HTMX)

    /rh/                        → dashboard_rh (listagem vagas)
    /rh/vaga/<id>/matching/     → rodar_matching (POST, HTMX)
    /rh/vaga/<id>/ranking/      → ranking_candidatos
    /rh/vaga/<id>/match/<cid>/  → detalhe_candidato_match
    /rh/pipeline/               → pipeline_kanban (todos)
    /rh/pipeline/<id>/          → pipeline_kanban (por vaga)

    /candidato/<id>/            → dashboard_candidato
    /candidato/<id>/habilidades/→ habilidades_candidato_htmx

    /dashboard/                 → dashboard_geral (Chart.js)
    /api/stats/                 → api_stats (JSON para Chart.js)
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ==========================================================================
    # FASE 3: UPLOAD DE CV
    # ==========================================================================
    path('', views.home, name='home'),
    path('upload/', views.upload_cv, name='upload_cv'),
    path('upload/processar/', views.processar_upload, name='processar_upload'),
    path('upload/status/<str:candidato_id>/', views.status_cv_htmx, name='status_cv_htmx'),

    # ==========================================================================
    # FASE 4: DASHBOARD DO RH
    # ==========================================================================
    path('rh/', views.dashboard_rh, name='dashboard_rh'),
    path('rh/vaga/<int:vaga_id>/matching/', views.rodar_matching, name='rodar_matching'),
    path('rh/vaga/<int:vaga_id>/ranking/', views.ranking_candidatos, name='ranking_candidatos'),
    path('rh/vaga/<int:vaga_id>/match/<str:candidato_id>/', views.detalhe_candidato_match, name='detalhe_match'),
    path('rh/pipeline/', views.pipeline_kanban, name='pipeline_kanban'),
    path('rh/pipeline/<int:vaga_id>/', views.pipeline_kanban, name='pipeline_kanban_vaga'),

    # ==========================================================================
    # FASE 4: DASHBOARD DO CANDIDATO
    # ==========================================================================
    path('candidato/<str:candidato_id>/', views.dashboard_candidato, name='dashboard_candidato'),
    path('candidato/<str:candidato_id>/habilidades/', views.habilidades_candidato_htmx, name='habilidades_htmx'),

    # ==========================================================================
    # FASE 4: DASHBOARD GERAL (ESTATÍSTICAS)
    # ==========================================================================
    path('dashboard/', views.dashboard_geral, name='dashboard_geral'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
