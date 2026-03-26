"""
Migration para resetar senha do usuário RH.
"""
import os

from django.db import migrations
from django.contrib.auth.hashers import make_password


def resetar_senha(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    NOVA_SENHA = os.getenv('RH_ADMIN_PASSWORD')

    if not NOVA_SENHA:
        print('⚠️ RH_ADMIN_PASSWORD não definido. Senha não foi resetada.')
        return

    # Tenta encontrar o usuário por diferentes usernames
    for username in [os.getenv('RH_ADMIN_USERNAME', 'admin_rh'), 'admin_rh', 'rh_admin']:
        try:
            user = User.objects.get(username=username)
            user.password = make_password(NOVA_SENHA)
            user.save()
            print(f'✅ Senha resetada para {username}')
            return
        except User.DoesNotExist:
            continue

    # Se não encontrou, cria um novo
    rh_email = os.getenv('RH_ADMIN_EMAIL', 'rh@empresa.com')
    rh_username = os.getenv('RH_ADMIN_USERNAME', 'rh_admin')
    user = User(
        username=rh_username,
        email=rh_email,
        password=make_password(NOVA_SENHA),
        is_staff=True,
        is_superuser=True,
    )
    user.save()
    print(f'✅ Novo usuário {rh_username} criado.')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_criar_usuario_rh'),
    ]

    operations = [
        migrations.RunPython(resetar_senha, migrations.RunPython.noop),
    ]
