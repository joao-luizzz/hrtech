# Scripts Utilitarios

Scripts de apoio operacional e desenvolvimento local.

## Arquivos

- popular_banco.py: popula dados fake no PostgreSQL e Neo4j para testes.

## Uso

No raiz do projeto:

```bash
python scripts/popular_banco.py
```

Opcional via shell do Django:

```bash
python manage.py shell < scripts/popular_banco.py
```
