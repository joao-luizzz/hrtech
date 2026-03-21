"""
HRTech - Admin Configuration
============================

Registra os models no Django Admin para gerenciamento.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Candidato, Vaga, AuditoriaMatch, Profile, HistoricoAcao


# Inline para Profile no User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'


# Extende o UserAdmin para incluir Profile
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'get_role']

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'
    get_role.short_description = 'Role'


# Re-registra o User com o novo admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'receber_notificacoes', 'created_at']
    list_filter = ['role', 'receber_notificacoes']
    search_fields = ['user__email', 'user__first_name']
    raw_id_fields = ['user']


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'senioridade', 'etapa_processo', 'status_cv', 'disponivel', 'created_at']
    list_filter = ['senioridade', 'etapa_processo', 'status_cv', 'disponivel']
    search_fields = ['nome', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Dados Pessoais', {
            'fields': ('id', 'nome', 'email', 'telefone', 'user')
        }),
        ('Perfil Profissional', {
            'fields': ('senioridade', 'anos_experiencia', 'disponivel')
        }),
        ('Processo Seletivo', {
            'fields': ('etapa_processo', 'status_cv', 'cv_s3_key')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Vaga)
class VagaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'area', 'senioridade_desejada', 'status', 'criado_por', 'created_at']
    list_filter = ['area', 'senioridade_desejada', 'status']
    search_fields = ['titulo', 'descricao']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['criado_por']
    ordering = ['-created_at']


@admin.register(AuditoriaMatch)
class AuditoriaMatchAdmin(admin.ModelAdmin):
    list_display = ['candidato', 'vaga', 'score', 'versao_algoritmo', 'created_at']
    list_filter = ['versao_algoritmo', 'created_at']
    search_fields = ['candidato__nome', 'vaga__titulo']
    readonly_fields = ['candidato', 'vaga', 'score', 'snapshot_skills', 'versao_algoritmo', 'detalhes_calculo', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HistoricoAcao)
class HistoricoAcaoAdmin(admin.ModelAdmin):
    list_display = ['tipo_acao', 'usuario', 'candidato', 'vaga', 'ip_address', 'created_at']
    list_filter = ['tipo_acao', 'created_at']
    search_fields = ['usuario__email', 'candidato__nome', 'vaga__titulo']
    readonly_fields = ['usuario', 'tipo_acao', 'candidato', 'vaga', 'detalhes', 'ip_address', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Customiza o título do admin
admin.site.site_header = 'HRTech ATS - Administracao'
admin.site.site_title = 'HRTech Admin'
admin.site.index_title = 'Painel de Administracao'
