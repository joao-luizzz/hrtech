"""
HRTech - Admin Configuration
============================

Registra os models no Django Admin para gerenciamento.
"""

from django.contrib import admin
from .models import Candidato, Vaga, AuditoriaMatch


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'senioridade', 'anos_experiencia', 'disponivel', 'status_cv', 'created_at']
    list_filter = ['senioridade', 'disponivel', 'status_cv']
    search_fields = ['nome', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'area', 'senioridade_desejada', 'status', 'created_at']
    list_filter = ['area', 'senioridade_desejada', 'status']
    search_fields = ['titulo', 'descricao']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(AuditoriaMatch)
class AuditoriaMatchAdmin(admin.ModelAdmin):
    list_display = ['candidato', 'vaga', 'score', 'versao_algoritmo', 'created_at']
    list_filter = ['versao_algoritmo', 'created_at']
    search_fields = ['candidato__nome', 'vaga__titulo']
    readonly_fields = ['candidato', 'vaga', 'score', 'snapshot_skills', 'versao_algoritmo', 'detalhes_calculo', 'created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        # Auditorias são criadas apenas pelo sistema
        return False
    
    def has_change_permission(self, request, obj=None):
        # Auditorias são imutáveis
        return False
