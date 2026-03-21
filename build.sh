#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Instala todas as dependências do projeto
pip install -r requirements.txt

# 2. Reúne os ficheiros estáticos (CSS, JS) para o Render
python manage.py collectstatic --no-input

# 3. Atualiza as tabelas da Base de Dados na nuvem
python manage.py migrate

# 4. Roda o nosso comando para criar o admin do RH (Só roda na nuvem)
python manage.py setup_rh