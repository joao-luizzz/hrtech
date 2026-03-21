"""
HRTech - URLs do App Core
=========================

Estrutura:
    /                           → home (página inicial)

    # Upload de CV (público)
    /upload/                    → upload_cv
    /upload/processar/          → processar_upload (POST)
    /upload/status/<id>/        → status_cv_htmx

    # Dashboard RH (protegido)
    /rh/                        → dashboard_rh
    /rh/vaga/<id>/matching/     → rodar_matching (POST)
    /rh/vaga/<id>/ranking/      → ranking_candidatos
    /rh/vaga/<id>/match/<cid>/  → detalhe_candidato_match
    /rh/pipeline/               → pipeline_kanban
    /rh/pipeline/<id>/          → pipeline_kanban (por vaga)
    /rh/pipeline/mover/         → mover_kanban (POST)
    /rh/historico/              → historico_acoes

    # CRUD de Vagas (protegido)
    /rh/vagas/                  → lista_vagas
    /rh/vagas/nova/             → criar_vaga
    /rh/vagas/<id>/editar/      → editar_vaga
    /rh/vagas/<id>/excluir/     → excluir_vaga (POST)

    # Busca de Candidatos (protegido)
    /rh/candidatos/             → buscar_candidatos

    # Dashboard Candidato
    /candidato/<id>/            → dashboard_candidato
    /candidato/<id>/habilidades/→ habilidades_candidato_htmx

    # Dashboard Geral (protegido)
    /dashboard/                 → dashboard_geral
    /api/stats/                 → api_stats (JSON)
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ==========================================================================
    # PÁGINAS PÚBLICAS
    # ==========================================================================
    path('', views.home, name='home'),
    path('upload/', views.upload_cv, name='upload_cv'),
    path('upload/processar/', views.processar_upload, name='processar_upload'),
    path('upload/status/<str:candidato_id>/', views.status_cv_htmx, name='status_cv_htmx'),

    # ==========================================================================
    # DASHBOARD DO RH (PROTEGIDO)
    # ==========================================================================
    path('rh/', views.dashboard_rh, name='dashboard_rh'),
    path('rh/vaga/<int:vaga_id>/matching/', views.rodar_matching, name='rodar_matching'),
    path('rh/vaga/<int:vaga_id>/ranking/', views.ranking_candidatos, name='ranking_candidatos'),
    path('rh/vaga/<int:vaga_id>/match/<str:candidato_id>/', views.detalhe_candidato_match, name='detalhe_match'),
    path('rh/pipeline/', views.pipeline_kanban, name='pipeline_kanban'),
    path('rh/pipeline/<int:vaga_id>/', views.pipeline_kanban, name='pipeline_kanban_vaga'),
    path('rh/pipeline/mover/', views.mover_kanban, name='mover_kanban'),
    path('rh/historico/', views.historico_acoes, name='historico_acoes'),

    # ==========================================================================
    # CRUD DE VAGAS (PROTEGIDO)
    # ==========================================================================
    path('rh/vagas/', views.lista_vagas, name='lista_vagas'),
    path('rh/vagas/nova/', views.criar_vaga, name='criar_vaga'),
    path('rh/vagas/<int:vaga_id>/editar/', views.editar_vaga, name='editar_vaga'),
    path('rh/vagas/<int:vaga_id>/excluir/', views.excluir_vaga, name='excluir_vaga'),

    # ==========================================================================
    # BUSCA DE CANDIDATOS (PROTEGIDO)
    # ==========================================================================
    path('rh/candidatos/', views.buscar_candidatos, name='buscar_candidatos'),

    # ==========================================================================
    # DASHBOARD DO CANDIDATO
    # ==========================================================================
    path('candidato/<str:candidato_id>/', views.dashboard_candidato, name='dashboard_candidato'),
    path('candidato/<str:candidato_id>/habilidades/', views.habilidades_candidato_htmx, name='habilidades_htmx'),

    # ==========================================================================
    # DASHBOARD GERAL (PROTEGIDO)
    # ==========================================================================
    path('dashboard/', views.dashboard_geral, name='dashboard_geral'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
