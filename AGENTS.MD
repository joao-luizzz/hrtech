# AGENTS.md

## Segurança — regras inegociáveis
- NUNCA hardcode credentials, tokens ou secrets
- SEMPRE usar variáveis de ambiente via python-decouple ou os.environ
- NUNCA logar dados pessoais (CPF, email, conteúdo de CV)
- SEMPRE validar e sanitizar input do usuário antes de qualquer operação
- NUNCA expor stack traces em produção (DEBUG=False)

## Padrões do projeto
- Arquitetura: Service Layer separada das Views
- Testes: todo novo código precisa de teste correspondente
- Migrações: nunca editar migração já aplicada em produção
```

O agente vai seguir essas regras em toda sessão automaticamente.

---

## 🔍 2. Prompt de auditoria de segurança

Antes de fazer deploy, roda isso no agente Local com o modelo mais forte:
```
#codebase Faça uma auditoria de segurança completa focando em:
1. Injeção SQL ou NoSQL
2. Credenciais ou secrets expostos no código
3. Endpoints sem autenticação que deveriam ter
4. Dados sensíveis sendo logados
5. Inputs do usuário não sanitizados
6. Configurações inseguras de CORS, CSRF ou SESSION
7. Dependências com vulnerabilidades conhecidas

Liste cada problema encontrado com o arquivo, linha e como corrigir.
```

---

## 🐛 3. Prompt de revisão de bugs de produção
```
#codebase Revise o código procurando:
1. Race conditions em operações assíncronas (Celery)
2. Queries N+1 no ORM do Django
3. Falta de tratamento de exceção em chamadas externas (OpenAI, AWS, Neo4j)
4. Memory leaks em loops ou conexões não fechadas
5. Timeouts não configurados em chamadas HTTP
6. Transações de banco não atomizadas onde deveriam ser

## Checklist de deploy
- [ ] Nenhum secret no código (rodar: git grep -i "password\|secret\|token\|key" -- '*.py')
- [ ] DEBUG=False no ambiente de produção
- [ ] Todas as variáveis do .env.example preenchidas no servidor
- [ ] Dependências atualizadas (pip audit)
- [ ] Testes passando (python manage.py test)
- [ ] Migrations aplicadas
- [ ] Worker do Celery rodando no Procfile
```

---

## 🔐 5. Específico pro Django
```
#codebase Verifique se o projeto segue o Django Security Checklist:
- ALLOWED_HOSTS configurado corretamente
- CSRF protection ativa em todos os forms
- X-Frame-Options, Secure cookies e HSTS configurados
- Senhas usando Argon2 ou PBKDF2
- Rate limiting em endpoints de login
- FileField com validação de tipo e tamanho