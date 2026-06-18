#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Atualiza ferramentas base para reduzir CVEs conhecidas de empacotamento
python -m pip install --upgrade pip setuptools

# 2. Instala todas as dependências do projeto
pip install -r requirements.txt

# 3. Reúne os ficheiros estáticos (CSS, JS) para o Render
python manage.py collectstatic --no-input
