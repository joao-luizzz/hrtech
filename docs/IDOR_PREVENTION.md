---
name: Security Best Practices - IDOR Prevention for Multi-Tenant
tech: Django
---

# IDOR Prevention Best Practices para HRTech

## Checklist para TODAS as views e services

### 1. Views que accessam entidades por ID

```python
# ❌ WRONG - Sem validação de tenant
@login_required
def view_candidate(request, candidato_id):
    candidato = Candidato.objects.get(pk=candidato_id)
    return render(request, 'candidato.html', {'candidato': candidato})

# ✅ CORRECT - Com validação de tenant
@login_required
@rh_required
def view_candidate(request, candidato_id):
    user_org = _get_user_organization(request.user)
    if not user_org:
        return render(request, 'error.html', status=403)
    
    candidato = get_object_or_404(
        Candidato, 
        pk=candidato_id,
        organization=user_org  # ← MANDATORY
    )
    return render(request, 'candidato.html', {'candidato': candidato})
```

### 2. Services que processam dados

```python
# ❌ WRONG - Sem organization parameter
class MyService:
    @staticmethod
    def process_candidate(candidato_id):
        candidato = Candidato.objects.get(pk=candidato_id)
        # ... process

# ✅ CORRECT - Com organization mandatory
class MyService:
    @staticmethod
    def process_candidate(candidato_id, organization):
        """
        SECURITY: organization é obrigatório para tenant isolation.
        """
        if organization is None:
            raise ValueError("organization parameter is required")
        
        candidato = get_object_or_404(
            Candidato,
            pk=candidato_id,
            organization=organization
        )
        # ... process
```

### 3. Queries que retornam listas

```python
# ❌ WRONG - Retorna dados de QUALQUER organização
def list_candidates(request):
    candidatos = Candidato.objects.all()
    
# ✅ CORRECT - Filtra por organização do usuário
def list_candidates(request):
    user_org = _get_user_organization(request.user)
    if not user_org:
        return empty_result  # ou error
    
    candidatos = Candidato.objects.filter(organization=user_org)
```

### 4. Operações em POST/PUT/DELETE

```python
# ❌ WRONG - Sem validação de ownership
@require_POST
def delete_comment(request, comment_id):
    comment = Comentario.objects.get(pk=comment_id)
    comment.delete()
    
# ✅ CORRECT - Valida tenant+ownership
@login_required
@rh_required
@require_POST
def delete_comment(request, comment_id):
    user_org = _get_user_organization(request.user)
    if not user_org:
        return error(status=403)
    
    # Garante que o comentário pertence a um candidato da org
    comment = get_object_or_404(
        Comentario,
        pk=comment_id,
        candidato__organization=user_org
    )
    
    # Opcional: verificar se usuário é o autor
    if comment.autor != request.user and not request.user.is_staff:
        return error(status=403)
    
    comment.delete()
```

### 5. Celery tasks e background jobs

```python
# ❌ WRONG - Sem validação de organização
@shared_task
def process_cv(candidato_id):
    candidato = Candidato.objects.get(pk=candidato_id)
    # ... process
    
# ✅ CORRECT - Valida organization antes de processar
@shared_task
def process_cv(candidato_id):
    try:
        candidato = Candidato.objects.get(pk=candidato_id)
    except Candidato.DoesNotExist:
        logger.error(f"Candidato {candidato_id} not found - possible cross-tenant attack")
        return {'status': 'error'}
    
    org = candidato.organization
    if not org:
        logger.error(f"Candidato without organization - invalid state")
        return {'status': 'error'}
    
    # Agora seguro para processar
    # ...
```

## Pattern: Adicionar organização a um serviço existente

Se você tem um serviço sem validação de tenant:

```python
# Passo 1: Adicione organization como parâmetro obrigatório
@staticmethod
def my_method(candidato_id, organization):  # ← ADD organization
    """
    SECURITY: organization é obrigatório para tenant isolation.
    """
```

```python  
# Passo 2: Adicione early validation
    if organization is None:
        raise ValueError("organization parameter is required")
```

```python
# Passo 3: Use em todas as queries
    candidato = get_object_or_404(
        Candidato,
        pk=candidato_id,
        organization=organization  # ← ALWAYS ADD
    )
```

```python
# Passo 4: Atualize TODAS as chamadas
    # ❌ OLD
    MyService.my_method(candidato_id)
    
    # ✅ NEW  
    MyService.my_method(candidato_id, organization=user_org)
```

```python
# Passo 5: Escreva testes
def test_my_method_cross_tenant_blocked(self):
    self.client.login(...)  # User de Org1
    
    # Tenta operar em Candidato de Org2
    response = self.client.post(
        f'/api/candidatos/{self.candidato_org2.id}/',
        data={'action': 'my_method'}
    )
    
    # Deve retornar 404 ou 403
    assert response.status_code in [403, 404]
```

## Red Flags - Patterns a evitar

| Pattern | Risk | Fix |
|---------|------|-----|
| `Candidato.objects.all()` | Retorna TODOS | `.filter(organization=org)` |
| `.objects.get(pk=?)` | Sem tenant check | `get_object_or_404(pk=?, org=org)` |
| `queryset.filter(email=?)` | Email enumeration | `.filter(email=?, organization=org)` |
| Sem `@rh_required` em view | Candidate vê dados RH | Adicione decorator |
| Service sem org param | Serve sem validação | Adicione org obrigatório |
| Task sem org validation | Background cross-tenant | Validar org antes processar |
| Query em loop sem prefetch | N+1 + tenant miss | Use `.select_related()/.prefetch_related()` |

## O Stack de Segurança HRTech

1. **Decorators** - `@login_required`, `@rh_required`, `@csrf_protect`
2. **View Logic** - `user_org = _get_user_organization(request.user)`
3. **Query Filtering** - `.filter(organization=user_org)`
4. **Service Validation** - Service params require `organization`
5. **Tests** - Sempre testar cross-tenant blocking

## Auditoria: Commands para verificar regras

```bash
# 1. Procure por .objects.all() que não filtra
grep -r "\.objects\.all()" core/ | grep -v "test_\|#"

# 2. Procure por .objects.get() sem filter
grep -r "\.objects\.get(pk=" core/ | grep -v ".filter("

# 3. Procure por views sem @rh_required
grep -r "def.*request.*:" core/views.py | grep -v "@rh_required\|@login_required"

# 4. Procure por services sem organization param
grep -r "def .*candidato_id" core/services/ | grep -v organization
```

## Deployment Checklist

Antes de fazer deploy, SEMPRE:

```
[ ] Rodou: python manage.py test core.tests.test_tenant_isolation
[ ] Rodou: python tenant_isolation_checker.py (zero CRITICAL findings)
[ ] Code review: Verificou org filters em todas queries
[ ] Commit message mencionou: "SECURITY: Added org validation"
[ ] Git tags: Marcou como "security-fix" no commit
```

---

**Last Updated:** 2026-04-12  
**Schema Version:** v1.0 (Post-Security-Audit)  
**Threat Model:** Multi-tenant IDOR/Cross-tenant data access (HIGH)
