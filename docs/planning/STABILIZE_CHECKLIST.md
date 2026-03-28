# Stabilize Checklist (Fase 1)

Objetivo: reduzir risco operacional e preparar a base para novas features.

## 1. Seguranca de configuracao

- [x] Remover credenciais hardcoded do comando setup_rh.
- [x] Configurar setup_rh por variaveis de ambiente:
  - RH_ADMIN_USERNAME
  - RH_ADMIN_EMAIL
  - RH_ADMIN_PASSWORD
  - SITE_DOMAIN
- [x] Revisar todos os comandos de management para evitar segredos no codigo.

## 2. Consistencia de dominio

- [x] Corrigir filtro de vagas em comentarios para usar status (ABERTA).
- [x] Rodar busca de campos legados (ativo, is_active custom, etc.) e padronizar.
- [ ] Consolidar enum de estados criticos de Vaga e Candidato com validacao central.

## 3. Operacao assincrona em producao

- [x] Definir process types no Procfile: web, worker e beat.
- [x] Ajustar configuracao do provedor (Render) para subir worker e beat separados.
- [x] Validar filas default/openai com smoke test de processamento completo.

## 4. Observabilidade minima

- [x] Incluir correlation id em logs de fluxo de CV e matching.
- [x] Padronizar logs de erro com contexto: candidato_id, vaga_id, task_id.
- [x] Definir dashboard basico de erros e jobs fantasmas.

## 5. Smoke tests obrigatorios pre-feature

- [x] Suite automatizada base executada com settings de teste:
  - manage.py check --settings=hrtech.settings_test
  - manage.py test core.tests.test_matching_engine.MatchingEngineTests --settings=hrtech.settings_test
  - manage.py test core.tests.test_pipeline_mock --settings=hrtech.settings_test
- [x] Upload de CV e polling de status ate CONCLUIDO/ERRO.
- [x] Rodar matching para vaga com auditoria criada.
- [x] Movimentar pipeline kanban e registrar historico.
- [x] Exportar candidatos e ranking sem erro.

## Evidencias desta rodada

- Ajuste estrutural de testes para discovery estavel:
  - core/tests.py -> core/tests/test_matching_engine.py
- Ajuste de ambiente de testes para nao depender de mock mode do .env:
  - OPENAI_MOCK_MODE = False em hrtech/settings_test.py
- Suite de matching: 14 testes OK.
- Suite pipeline mock: 36 testes OK.
- System check Django: OK com 3 warnings deprecados do allauth (sem erro bloqueante).
- Revisao de comandos de management: sem credenciais hardcoded remanescentes.
- Busca de campo legado em runtime: sem uso de `ativo`/`is_active` fora de migrações históricas.
- Middleware de correlacao implementado: `core/middleware.py` com header `X-Request-ID`.
- Logs de excecao em views enriquecidos com `request_id` e ids de entidade quando aplicável.
- Configuracoes deprecadas do allauth migradas para `ACCOUNT_LOGIN_METHODS` e `ACCOUNT_SIGNUP_FIELDS`.
- Dashboard RH agora exibe saude operacional com contadores de jobs em processamento, jobs fantasmas e erros de processamento.
- Blueprint de deploy Render criado em `render.yaml` com servicos separados: web, worker e beat.
- Nova suite de smoke (`core/tests/test_smoke_flows.py`) cobrindo upload+polling, matching, kanban, exportacoes e validacao de filas Celery (`default` e `openai`).

## Criterio de conclusao da fase

A fase termina quando todos os itens marcados [ ] estiverem concluidos em ambiente de homologacao.
