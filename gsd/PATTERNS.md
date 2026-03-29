# HRTech - Code Patterns & Examples

Exemplos prontos para copiar/colar ao implementar features no HRTech.

---

## 1. Criar um Novo Service

```python
# core/services/meu_service.py

import logging
from core.models import Candidato, Vaga

logger = logging.getLogger(__name__)


class MeuService:
    """
    Descrição breve do que este service faz.
    
    Métodos estáticos por design - sem estado.
    """
    
    @staticmethod
    def fazer_algo_importante(param1: str, param2: int) -> dict:
        """
        Descrição do método.
        
        Args:
            param1: Descrição
            param2: Descrição
        
        Returns:
            Dict com resultado
        
        Raises:
            ValueError: Se validação falha
        """
        logger.info(f"Iniciando fazer_algo_importante: param1={param1}")
        
        try:
            # Lógica aqui
            resultado = {"status": "sucesso", "dados": []}
            
            logger.info(f"Resultado: {len(resultado['dados'])} items")
            return resultado
        
        except Exception as e:
            logger.exception(f"Erro em fazer_algo_importante: {type(e).__name__}")
            raise
```

```python
# core/services/__init__.py - ADICIONE ESTA LINHA

from .meu_service import MeuService

__all__ = [
    # ... existing ...
    'MeuService',
]
```

```python
# Usar em views
from core.services import MeuService

resultado = MeuService.fazer_algo_importante("param", 123)
```

---

## 2. Implementar uma View com Service

```python
# core/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from core.models import Candidato, registrar_acao, HistoricoAcao
from core.decorators import rh_required, get_client_ip
from core.services import MeuService


@require_POST
@rh_required  # Apenas RH/Admin
def view_fazer_algo(request, candidato_id):
    """Fazer algo importante com candidato."""
    
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    
    try:
        # Chamar service (lógica isolada)
        resultado = MeuService.fazer_algo_importante(
            param1=str(candidato.id),
            param2=5
        )
        
        # Registrar ação (LGPD audit)
        registrar_acao(
            usuario=request.user,
            tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_EDITADO,
            candidato=candidato,
            detalhes={'acao': 'fazer_algo', 'resultado': resultado['status']},
            ip_address=get_client_ip(request)
        )
        
        messages.success(request, 'Ação realizada com sucesso!')
        return redirect('candidato_detail', pk=candidato_id)
    
    except ValueError as e:
        messages.error(request, f'Erro: {str(e)}')
        return redirect('candidato_detail', pk=candidato_id)
    
    except Exception as e:
        logger.exception(f"Erro inesperado: {type(e).__name__}")
        messages.error(request, 'Erro interno do servidor')
        return redirect('candidato_detail', pk=candidato_id)
```

---

## 3. Celery Task com Retry

```python
# core/tasks.py

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from openai import RateLimitError, APIConnectionError

from core.models import Candidato


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60  # Esperar 60s antes de retry
)
def minha_task(self, param_id: str) -> dict:
    """
    Task assíncrona com retry automático.
    
    Retries são automáticos para erros transientes.
    MaxRetriesExceededError é tratado para falha final.
    """
    logger.info(f"[Task {self.request.id}] Iniciando minha_task param={param_id[:8]}")
    
    try:
        # Buscar dados
        candidato = Candidato.objects.get(pk=param_id)
        
        # Atualizar status (para polling frontend)
        candidato.status_cv = 'processando'
        candidato.save(update_fields=['status_cv'])
        
        # Lógica da task
        resultado = processar_algo(candidato)
        
        # Atualizar status final
        candidato.status_cv = 'concluido'
        candidato.save(update_fields=['status_cv'])
        
        logger.info(f"[Task {self.request.id}] Sucesso: {resultado}")
        return {'status': 'success', 'result': resultado}
    
    except Candidato.DoesNotExist:
        logger.error(f"Candidato {param_id} não encontrado")
        return {'status': 'error', 'reason': 'candidato_nao_encontrado'}
    
    except (RateLimitError, APIConnectionError, TimeoutError) as e:
        # Erros transientes → Retry
        logger.warning(f"Erro transiente ({type(e).__name__}), reagendando retry...")
        try:
            raise self.retry(exc=e, countdown=30)
        except MaxRetriesExceededError:
            logger.error(f"Max retries excedido para {param_id[:8]}")
            candidato.status_cv = 'erro'
            candidato.save(update_fields=['status_cv'])
            return {'status': 'error', 'reason': 'max_retries'}
    
    except Exception as e:
        logger.exception(f"Erro inesperado: {type(e).__name__}")
        raise  # Celery fará retry automático


def processar_algo(candidato) -> str:
    """Função auxiliar da task."""
    # Implementação aqui
    return "resultado"
```

**Usar em view**:

```python
from core.tasks import minha_task

# Disparar task assíncrona (sem tracar)
minha_task.delay(candidato_id)

# Frontend faz polling do status_cv via HTMX
```

---

## 4. Neo4j Query com Context Manager

```python
# Em um service

from core.neo4j_connection import Neo4jConnection


class MeuService:
    @staticmethod
    def buscar_skills_candidato(candidato_uuid: str) -> list:
        """Busca skills do Neo4j."""
        
        query = """
        MATCH (c:Candidato {uuid: $uuid})-[r:TEM_HABILIDADE]->(h:Habilidade)
        WHERE r.nivel >= 3
        RETURN h.nome as nome, r.nivel as nivel, r.anos_experiencia as anos
        ORDER BY r.nivel DESC
        """
        
        with Neo4jConnection() as conn:
            return conn.run_query(query, {'uuid': str(candidato_uuid)})
    
    @staticmethod
    def salvar_skills_neo4j(candidato_uuid: str, skills: list) -> None:
        """Salva skills no Neo4j."""
        
        for skill in skills:
            query = """
            MERGE (c:Candidato {uuid: $uuid})
            MERGE (h:Habilidade {nome: $nome})
            MERGE (c)-[r:TEM_HABILIDADE]->(h)
            SET r.nivel = $nivel,
                r.anos_experiencia = $anos,
                r.ano_ultima_utilizacao = $ano_uso,
                r.inferido = $inferido
            """
            
            with Neo4jConnection() as conn:
                conn.run_write_query(query, {
                    'uuid': str(candidato_uuid),
                    'nome': skill['nome'],
                    'nivel': skill['nivel'],
                    'anos': skill['anos_experiencia'],
                    'ano_uso': skill['ano_ultima_utilizacao'],
                    'inferido': skill['inferido']
                })
```

---

## 5. Formulário com CSRF + Validação

```python
# core/views.py

from django.views.decorators.http import require_POST, require_http_methods
import json


@require_http_methods(["GET", "POST"])
@login_required
def view_criar_vaga(request):
    """Criar vaga com validação de skills JSON."""
    
    if request.method == 'GET':
        return render(request, 'vaga/form.html')
    
    # POST
    titulo = request.POST.get('titulo', '').strip()
    area = request.POST.get('area', '').strip()
    skills_json = request.POST.get('skills_obrigatorias', '[]')
    
    # Validar
    errors = []
    
    if not titulo or len(titulo) > 255:
        errors.append('Título inválido (1-255 caracteres)')
    
    if not area:
        errors.append('Área é obrigatória')
    
    # Validar JSON de skills
    skills_obrigatorias, skill_errors = _parse_skills_payload(
        skills_json,
        'Skills obrigatórias'
    )
    errors.extend(skill_errors)
    
    if errors:
        return render(request, 'vaga/form.html', {
            'errors': errors,
            'form_data': request.POST
        })
    
    # Criar vaga (usar service!)
    vaga = VagaService.criar_vaga(
        titulo=titulo,
        area=area,
        skills_obrigatorias=skills_obrigatorias,
        criado_por=request.user
    )
    
    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.VAGA_CRIADA,
        vaga=vaga,
        detalhes={'area': area, 'skills_count': len(skills_obrigatorias)},
        ip_address=get_client_ip(request)
    )
    
    messages.success(request, 'Vaga criada com sucesso!')
    return redirect('vaga_detail', pk=vaga.id)


def _parse_skills_payload(raw_payload: str, label: str) -> tuple:
    """
    Valida e parseia JSON de skills.
    
    Returns:
        (parsed_list, errors_list)
    """
    try:
        parsed = json.loads(raw_payload or '[]')
    except json.JSONDecodeError:
        return [], [f'{label} inválidas: JSON malformado']
    
    if not isinstance(parsed, list):
        return [], [f'{label} inválidas: deve ser uma lista']
    
    MAX_SKILLS = 50
    MAX_SKILL_NAME = 100
    
    if len(parsed) > MAX_SKILLS:
        return [], [f'{label} inválidas: máximo {MAX_SKILLS}']
    
    normalized = []
    errors = []
    
    for idx, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            errors.append(f'{label} item {idx}: deve ser um objeto')
            continue
        
        nome = str(item.get('nome', '')).strip()
        if not nome:
            errors.append(f'{label} item {idx}: nome obrigatório')
            continue
        
        if len(nome) > MAX_SKILL_NAME:
            errors.append(f'{label} item {idx}: nome > {MAX_SKILL_NAME} chars')
            continue
        
        try:
            nivel = int(item.get('nivel_minimo', 1))
            if not 1 <= nivel <= 5:
                raise ValueError()
        except (ValueError, TypeError):
            errors.append(f'{label} item {idx}: nível deve ser 1-5')
            continue
        
        normalized.append({'nome': nome, 'nivel_minimo': nivel})
    
    return normalized, errors
```

**HTML Template**:

```html
<!-- templates/vaga/form.html -->

{% extends "base.html" %}

{% block content %}
<div class="container">
    <h2>Criar Vaga</h2>
    
    {% if errors %}
    <div class="alert alert-danger">
        <ul>
        {% for error in errors %}
            <li>{{ error }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
    
    <form method="post" class="card">
        {% csrf_token %}
        
        <div class="mb-3">
            <label for="titulo" class="form-label">Título</label>
            <input type="text" class="form-control" id="titulo" name="titulo" 
                   value="{{ form_data.titulo }}" required>
        </div>
        
        <div class="mb-3">
            <label for="area" class="form-label">Área</label>
            <select class="form-select" id="area" name="area" required>
                <option selected disabled>Escolha uma área</option>
                <option value="backend" {% if form_data.area == 'backend' %}selected{% endif %}>Backend</option>
                <option value="frontend" {% if form_data.area == 'frontend' %}selected{% endif %}>Frontend</option>
                <option value="dados" {% if form_data.area == 'dados' %}selected{% endif %}>Dados</option>
            </select>
        </div>
        
        <div class="mb-3">
            <label for="skills" class="form-label">Skills Obrigatórias (JSON)</label>
            <textarea class="form-control" id="skills" name="skills_obrigatorias" 
                      rows="5">{{ form_data.skills_obrigatorias }}</textarea>
            <small class="form-text text-muted">
                Exemplo: [{"nome": "Python", "nivel_minimo": 3}]
            </small>
        </div>
        
        <button type="submit" class="btn btn-primary">Criar Vaga</button>
    </form>
</div>
{% endblock %}
```

---

## 6. Registrar Ação (LGPD Audit)

```python
# Ao realizar qualquer ação importante no sistema

from core.models import registrar_acao, HistoricoAcao
from core.decorators import get_client_ip


# Exemplo 1: Alterar etapa de candidato
registrar_acao(
    usuario=request.user,
    tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_ETAPA_ALTERADA,
    candidato=candidato,
    detalhes={'de': candidato.etapa_processo, 'para': nova_etapa},
    ip_address=get_client_ip(request)
)

# Exemplo 2: Deletar candidato
registrar_acao(
    usuario=request.user,
    tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_DELETADO,
    candidato=candidato,
    detalhes={'motivo': 'Exerceu direito ao esquecimento (LGPD)'},
    ip_address=get_client_ip(request)
)

# Exemplo 3: Visualizar CV (requerido por LGPD)
registrar_acao(
    usuario=request.user,
    tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CV_VISUALIZADO,
    candidato=candidato,
    detalhes={'arquivo': candidato.cv_s3_key},
    ip_address=get_client_ip(request)
)

# Exemplo 4: Executar matching
registrar_acao(
    usuario=request.user,
    tipo_acao=HistoricoAcao.TipoAcao.MATCHING_EXECUTADO,
    vaga=vaga,
    detalhes={'candidatos_analisados': 50, 'tempo_ms': 1234},
    ip_address=get_client_ip(request)
)
```

---

## 7. S3 Presigned URL (Seguro)

```python
# core/views.py

from core.services import get_s3_service
from core.models import Candidato


def view_download_cv(request, candidato_id):
    """Download seguro de CV via presigned URL."""
    
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    
    # Validar acesso (RH ou proprietário)
    if not (request.user.is_superuser or 
            request.user.profile.is_rh or 
            request.user.candidato == candidato):
        return HttpResponseForbidden('Acesso negado')
    
    # Registrar visualização (LGPD)
    registrar_acao(
        usuario=request.user,
        tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_CV_VISUALIZADO,
        candidato=candidato,
        ip_address=get_client_ip(request)
    )
    
    # Gerar URL segura com TTL de 15 minutos
    s3 = get_s3_service()
    presigned_url = s3.get_presigned_url(
        candidato.cv_s3_key,
        ttl=900  # 15 minutos
    )
    
    # Redirecionar para S3 (usuário faz download direto)
    return redirect(presigned_url)
```

---

## 8. Limpar Dados Pessoais (LGPD)

```python
# core/tasks.py - Já implementado, mas aqui está como usar

from core.tasks import limpar_dados_pessoais


def processar_cv_task(self, candidato_id: str) -> dict:
    """..."""
    
    # Extrair texto (pode conter CPF, RG, etc)
    texto_bruto = extrair_texto_cv(cv_path)
    
    # CRÍTICO: Limpar dados pessoais ANTES de enviar para OpenAI
    texto_limpo = limpar_dados_pessoais(texto_bruto)
    
    # Agora seguro enviar para IA
    cv_parseado = chamar_openai_extracao(texto_limpo)
```

A função `limpar_dados_pessoais`:
- Remove CPF: `000.000.000-00` → `[CPF REMOVIDO]`
- Remove RG: `XX.XXX.XXX-X` → `[RG REMOVIDO]`
- Remove datas de nascimento
- Remove CTPS, PIS, PASEP

**NUNCA** loga o texto original!

---

## 9. Deletar Candidato (Direito ao Esquecimento - LGPD)

```python
# core/views.py ou service

from django.db import transaction


@transaction.atomic  # Garante atomicidade: tudo ou nada
def view_deletar_candidato(request, candidato_id):
    """Deletar candidato com compliance LGPD."""
    
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    
    # Validar acesso (apenas RH/Admin)
    if not request.user.profile.is_rh:
        return HttpResponseForbidden()
    
    try:
        # 1. Registrar ação (ANTES de deletar)
        registrar_acao(
            usuario=request.user,
            tipo_acao=HistoricoAcao.TipoAcao.CANDIDATO_DELETADO,
            candidato=candidato,
            detalhes={'motivo': 'Direito ao esquecimento (LGPD)'},
            ip_address=get_client_ip(request)
        )
        
        # 2. Deletar do PostgreSQL
        candidato_uuid = str(candidato.id)
        candidato_nome = candidato.nome
        cv_s3_key = candidato.cv_s3_key
        
        candidato.delete()
        
        # 3. Deletar nó Neo4j (assíncrono)
        deletar_candidato_neo4j_task.delay(candidato_uuid)
        
        # 4. Deletar CV do S3 (assíncrono)
        if cv_s3_key:
            deletar_cv_s3_task.delay(cv_s3_key)
        
        messages.success(request, f'{candidato_nome} deletado com sucesso')
        
    except Exception as e:
        logger.exception(f"Erro ao deletar candidato: {type(e).__name__}")
        messages.error(request, 'Erro ao deletar candidato')
    
    return redirect('candidatos_list')


# Tasks assíncronas para limpeza

@shared_task(bind=True, max_retries=3)
def deletar_candidato_neo4j_task(self, candidato_uuid: str):
    """Deletar nó Candidato do Neo4j."""
    try:
        query = "MATCH (c:Candidato {uuid: $uuid}) DETACH DELETE c"
        run_write_query(query, {'uuid': candidato_uuid})
        logger.info(f"Candidato {candidato_uuid[:8]} deletado do Neo4j")
    except Exception as e:
        logger.warning(f"Retry deletar Neo4j: {type(e).__name__}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def deletar_cv_s3_task(self, cv_s3_key: str):
    """Deletar arquivo CV do S3."""
    try:
        s3 = get_s3_service()
        s3.delete_file(cv_s3_key)
        logger.info(f"CV {cv_s3_key} deletado do S3")
    except Exception as e:
        logger.warning(f"Retry deletar S3: {type(e).__name__}")
        raise self.retry(exc=e)
```

---

## 10. Polling HTMX para Status de Task

**Frontend** (template):

```html
<!-- Polling a cada 2 segundos até status ser 'concluido' -->
<div id="status-container" 
     hx-get="{% url 'candidato_status_cv' candidato.id %}"
     hx-trigger="every 2s"
     hx-swap="outerHTML">
    <p>Status: {{ candidato.get_status_cv_display }}</p>
</div>

<script>
    // Parar polling quando status for 'concluido'
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.xhr.status === 200) {
            const status = evt.detail.xhr.responseText.includes('Concluído');
            if (status) {
                htmx.ajax('GET', window.location, {target: 'body', swap: 'outerHTML'});
            }
        }
    });
</script>
```

**Backend** (view):

```python
@require_GET
@login_required
def candidato_status_cv(request, candidato_id):
    """Retorna HTML com status atual do CV."""
    
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    
    if candidato.status_cv == 'concluido':
        return render(request, 'partials/cv_status_concluido.html', {
            'candidato': candidato
        })
    elif candidato.status_cv == 'erro':
        return render(request, 'partials/cv_status_erro.html', {
            'candidato': candidato
        })
    else:
        return render(request, 'partials/cv_status_processando.html', {
            'candidato': candidato,
            'status': candidato.get_status_cv_display()
        })
```

---

## 11. Dark Mode CSS

```html
<!-- Usar variáveis CSS definidas em base.html -->

<style>
    .meu-elemento {
        background-color: var(--card-bg);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }
    
    .meu-elemento:hover {
        background-color: var(--bg-tertiary);
        box-shadow: 0 4px 6px var(--card-shadow);
    }
</style>
```

**Variáveis disponíveis** (definidas em `base.html`):

```css
--bg-primary           /* #ffffff / #1a1d23 */
--bg-secondary         /* #f8f9fa / #212529 */
--bg-tertiary          /* #e9ecef / #2c3034 */
--text-primary         /* #212529 / #e9ecef */
--text-secondary       /* #6c757d / #adb5bd */
--text-muted           /* #adb5bd / #6c757d */
--border-color         /* #dee2e6 / #495057 */
--card-bg              /* #ffffff / #2c3034 */
--card-shadow          /* rgba(...) */
```

---

## 12. Teste Unitário com Mock

```python
# core/tests/test_meu_service.py

from django.test import TestCase
from unittest.mock import patch, MagicMock

from core.models import Candidato
from core.services import MeuService


class MeuServiceTestCase(TestCase):
    
    def setUp(self):
        """Setup antes de cada teste."""
        self.candidato = Candidato.objects.create(
            nome='João Silva',
            email='joao@example.com',
            senioridade='pleno'
        )
    
    def test_fazer_algo_sucesso(self):
        """Teste caso de sucesso."""
        resultado = MeuService.fazer_algo_importante('param', 5)
        
        self.assertEqual(resultado['status'], 'sucesso')
        self.assertIsInstance(resultado['dados'], list)
    
    @patch('core.services.meu_service.neo4j_connection.Neo4jConnection')
    def test_fazer_algo_com_neo4j(self, mock_neo4j):
        """Teste com Neo4j mockado."""
        
        # Setup mock
        mock_conn = MagicMock()
        mock_neo4j.return_value.__enter__.return_value = mock_conn
        mock_conn.run_query.return_value = [
            {'nome': 'Python', 'nivel': 4}
        ]
        
        # Executar
        resultado = MeuService.fazer_algo_importante('param', 5)
        
        # Validar
        self.assertEqual(resultado['status'], 'sucesso')
        mock_neo4j.assert_called_once()
    
    @patch('core.services.meu_service.get_s3_service')
    def test_fazer_algo_com_s3(self, mock_s3):
        """Teste com S3 mockado."""
        
        mock_s3_instance = MagicMock()
        mock_s3.return_value = mock_s3_instance
        mock_s3_instance.upload_file.return_value = 's3://bucket/key'
        
        resultado = MeuService.fazer_algo_importante('param', 5)
        
        self.assertEqual(resultado['status'], 'sucesso')
        mock_s3_instance.upload_file.assert_called_once()
    
    def test_fazer_algo_erro_validacao(self):
        """Teste erro de validação."""
        
        with self.assertRaises(ValueError):
            MeuService.fazer_algo_importante('', -1)  # Params inválidos
```

**Rodar testes**:

```bash
python manage.py test core.tests.test_meu_service
python manage.py test core.tests  # Todos os testes
python manage.py test core.tests.test_meu_service.MeuServiceTestCase.test_fazer_algo_sucesso
```

---

## Checklist ao Adicionar Feature

```
[ ] Service criado em core/services/
[ ] Service exportado em core/services/__init__.py
[ ] View implementada com @rh_required ou @login_required
[ ] Ação registrada em HistoricoAcao
[ ] Modelo criado/atualizado em core/models.py
[ ] Migration criada: makemigrations && migrate
[ ] Modelo registrado em core/admin.py
[ ] Testes unitários criados em core/tests/
[ ] Testes passando: python manage.py test
[ ] Template criado com Dark Mode CSS
[ ] CSRF token em forms: {% csrf_token %}
[ ] Validação frontend + backend
[ ] LGPD: dados pessoais limpos, audit trail registrado
[ ] Documentação (docstrings + comentários)
[ ] Celery task (se assíncrono): @shared_task, max_retries, retry handling
[ ] Neo4j (se necessário): UUID sincronia, constraints criadas
[ ] S3 (se arquivo): presigned URL com TTL, não guardar URL completa
```

---

Todos estes exemplos seguem os **padrões arquiteturais** definidos em `ARCHITECTURE.md`.
