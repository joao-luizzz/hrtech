#!/usr/bin/env python
"""QA Test Script - Rigorously test all recent implementations"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrtech.settings')
django.setup()

from django.template.loader import get_template
from django.urls import reverse
from core.models import Candidato, Comentario, Favorito
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("QA RIGOROSO - TESTE DE TODAS AS FUNCIONALIDADES")
print("=" * 80)

errors = []
warnings = []

# Test 1: Template Existence
print("\n[TEST 1] Verificando existência de templates...")
templates_to_check = [
    'core/comentarios/lista.html',
    'core/partials/comentario_item.html',
    'core/favoritos/lista.html',
    'core/candidato/minha_area.html',
    'core/candidato/vincular.html',
    'core/candidato/aplicacoes.html',
    'core/relatorios/candidato_print.html',
    'core/candidatos/busca.html',
    'core/ranking_candidatos.html',
]

for template_name in templates_to_check:
    try:
        get_template(template_name)
        print(f"  ✓ {template_name}")
    except Exception as e:
        errors.append(f"Template {template_name} não encontrado: {e}")
        print(f"  ✗ {template_name} - ERRO: {e}")

# Test 2: URL Patterns
print("\n[TEST 2] Verificando URLs...")
urls_to_check = [
    ('core:listar_comentarios', {'candidato_id': 'test-uuid'}),
    ('core:adicionar_comentario', {'candidato_id': 'test-uuid'}),
    ('core:excluir_comentario', {'comentario_id': 1}),
    ('core:toggle_favorito', {'candidato_id': 'test-uuid'}),
    ('core:meus_favoritos', {}),
    ('core:minha_area', {}),
    ('core:vincular_candidato', {}),
    ('core:minhas_aplicacoes', {}),
    ('core:exportar_candidatos', {}),
    ('core:exportar_ranking', {'vaga_id': 1}),
    ('core:relatorio_candidato', {'candidato_id': 'test-uuid'}),
    ('core:buscar_candidatos', {}),
]

for url_name, kwargs in urls_to_check:
    try:
        url = reverse(url_name, kwargs=kwargs)
        print(f"  ✓ {url_name} -> {url}")
    except Exception as e:
        errors.append(f"URL {url_name} não encontrada: {e}")
        print(f"  ✗ {url_name} - ERRO: {e}")

# Test 3: Model Checks
print("\n[TEST 3] Verificando models...")
try:
    # Check Comentario model
    comentario_fields = [f.name for f in Comentario._meta.get_fields()]
    required_comentario = ['usuario', 'candidato', 'texto', 'privado', 'created_at']
    for field in required_comentario:
        if field in comentario_fields:
            print(f"  ✓ Comentario.{field}")
        else:
            errors.append(f"Campo {field} não encontrado em Comentario")
            print(f"  ✗ Comentario.{field} - FALTANDO")

    # Check Favorito model
    favorito_fields = [f.name for f in Favorito._meta.get_fields()]
    required_favorito = ['usuario', 'candidato', 'created_at']
    for field in required_favorito:
        if field in favorito_fields:
            print(f"  ✓ Favorito.{field}")
        else:
            errors.append(f"Campo {field} não encontrado em Favorito")
            print(f"  ✗ Favorito.{field} - FALTANDO")

    # Check Candidato.user relationship
    candidato_fields = [f.name for f in Candidato._meta.get_fields()]
    if 'user' in candidato_fields:
        print(f"  ✓ Candidato.user (OneToOneField)")
    else:
        warnings.append("Campo 'user' não encontrado em Candidato - vinculação pode não funcionar")
        print(f"  ⚠ Candidato.user - FALTANDO (vinculação não funcionará)")

except Exception as e:
    errors.append(f"Erro ao verificar models: {e}")
    print(f"  ✗ ERRO: {e}")

# Test 4: View Functions
print("\n[TEST 4] Verificando views...")
from core import views
view_functions = [
    'listar_comentarios',
    'adicionar_comentario',
    'excluir_comentario',
    'toggle_favorito',
    'meus_favoritos',
    'minha_area',
    'vincular_candidato',
    'minhas_aplicacoes',
    'exportar_candidatos_excel',
    'exportar_ranking_excel',
    'relatorio_candidato_print',
    'buscar_candidatos',
]

for view_name in view_functions:
    if hasattr(views, view_name):
        print(f"  ✓ {view_name}")
    else:
        errors.append(f"View {view_name} não encontrada")
        print(f"  ✗ {view_name} - FALTANDO")

# Test 5: Dependencies
print("\n[TEST 5] Verificando dependências...")
try:
    import openpyxl
    print(f"  ✓ openpyxl {openpyxl.__version__}")
except ImportError:
    errors.append("openpyxl não instalado - exportação Excel não funcionará")
    print(f"  ✗ openpyxl - NÃO INSTALADO")

# Test 6: Security Checks
print("\n[TEST 6] Verificando segurança das views...")
security_issues = []

# Check if views have proper decorators
import inspect
for view_name in view_functions:
    if hasattr(views, view_name):
        func = getattr(views, view_name)
        source = inspect.getsource(func)

        # Check for @login_required on protected views
        if view_name in ['listar_comentarios', 'adicionar_comentario', 'exportar_candidatos_excel']:
            if '@login_required' not in source and '@rh_required' not in source:
                security_issues.append(f"{view_name} pode não estar protegida adequadamente")
                print(f"  ⚠ {view_name} - POSSÍVEL FALTA DE PROTEÇÃO")
            else:
                print(f"  ✓ {view_name} - protegida")

if security_issues:
    warnings.extend(security_issues)

# Test 7: Check for common bugs
print("\n[TEST 7] Verificando bugs comuns...")

# Check for field name consistency
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='core_comentario'")
        columns = [row[0] for row in cursor.fetchall()]
        if 'created_at' in columns:
            print("  ✓ Comentario usa 'created_at' (correto)")
        elif 'criado_em' in columns:
            errors.append("Comentario usa 'criado_em' ao invés de 'created_at' - inconsistente com templates")
            print("  ✗ Comentario usa 'criado_em' - INCONSISTENTE COM TEMPLATES")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='core_favorito'")
        columns = [row[0] for row in cursor.fetchall()]
        if 'created_at' in columns:
            print("  ✓ Favorito usa 'created_at' (correto)")
        elif 'criado_em' in columns:
            errors.append("Favorito usa 'criado_em' ao invés de 'created_at' - inconsistente com templates")
            print("  ✗ Favorito usa 'criado_em' - INCONSISTENTE COM TEMPLATES")
except Exception as e:
    warnings.append(f"Não foi possível verificar colunas do banco: {e}")
    print(f"  ⚠ Não foi possível verificar banco de dados: {e}")

# Test 8: Advanced Filter Logic
print("\n[TEST 8] Verificando lógica de filtros avançados...")
from core.views import buscar_candidatos
source = inspect.getsource(buscar_candidatos)

if 'skill_logic' in source:
    print("  ✓ Suporte para skill_logic (AND/OR)")
else:
    errors.append("Filtros: skill_logic não implementado")
    print("  ✗ skill_logic - FALTANDO")

if 'nivel_minimo' in source:
    print("  ✓ Suporte para nivel_minimo")
else:
    errors.append("Filtros: nivel_minimo não implementado")
    print("  ✗ nivel_minimo - FALTANDO")

if 'disponivel' in source:
    print("  ✓ Suporte para filtro disponivel")
else:
    warnings.append("Filtros: disponivel pode não estar implementado")
    print("  ⚠ disponivel - pode estar faltando")

# SUMMARY
print("\n" + "=" * 80)
print("RESUMO DO QA")
print("=" * 80)

print(f"\n🔴 ERROS CRÍTICOS: {len(errors)}")
for error in errors:
    print(f"  - {error}")

print(f"\n🟡 WARNINGS: {len(warnings)}")
for warning in warnings:
    print(f"  - {warning}")

if errors:
    print("\n❌ TESTE FALHOU - Existem erros críticos que precisam ser corrigidos!")
    sys.exit(1)
elif warnings:
    print("\n⚠️  TESTE PASSOU COM WARNINGS - Revise os avisos")
    sys.exit(0)
else:
    print("\n✅ TODOS OS TESTES PASSARAM!")
    sys.exit(0)
