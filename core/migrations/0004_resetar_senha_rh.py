"""
Migration para resetar senha do usuário RH.
"""
import os

from django.db import migrations
from django.contrib.auth.hashers import make_password


def resetar_senha(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    email = os.getenv('RH_ADMIN_EMAIL', 'rh@empresa.com')
    username = os.getenv('RH_ADMIN_USERNAME', email)
    nova_senha = os.getenv('RH_ADMIN_PASSWORD')

    if not nova_senha:
        print('⚠️ RH_ADMIN_PASSWORD ausente. Reset de senha ignorado.')
        return

    # Tenta encontrar o usuário pelos identificadores configurados
    candidatos = [username, email]
    for candidato in candidatos:
        try:
            user = User.objects.get(username=candidato)
            user.password = make_password(nova_senha)
            user.save()
            print('✅ Senha de usuário RH atualizada.')
            return
        except User.DoesNotExist:
            continue

    # Se não encontrou, cria um novo
    user = User(
        username=username,
        email=email,
        password=make_password(nova_senha),
        is_staff=True,
        is_superuser=True,
    )
    user.save()
    print('✅ Novo usuário RH criado.')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_criar_usuario_rh'),
    ]

    operations = [
        migrations.RunPython(resetar_senha, migrations.RunPython.noop),
    ]
