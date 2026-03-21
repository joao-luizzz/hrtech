"""
Migration para resetar senha do usuário RH.
"""
from django.db import migrations
from django.contrib.auth.hashers import make_password


def resetar_senha(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    NOVA_SENHA = 'NovaSenha123!'

    # Tenta encontrar o usuário por diferentes usernames
    for username in ['admin_rh', 'rh@empresa.com', 'rh@hrtech.com']:
        try:
            user = User.objects.get(username=username)
            user.password = make_password(NOVA_SENHA)
            user.save()
            print(f'✅ Senha resetada para {username} - use: {NOVA_SENHA}')
            return
        except User.DoesNotExist:
            continue

    # Se não encontrou, cria um novo
    user = User(
        username='rh_admin',
        email='rh@hrtech.com',
        password=make_password(NOVA_SENHA),
        is_staff=True,
        is_superuser=True,
    )
    user.save()
    print(f'✅ Novo usuário rh_admin criado com senha: {NOVA_SENHA}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_criar_usuario_rh'),
    ]

    operations = [
        migrations.RunPython(resetar_senha, migrations.RunPython.noop),
    ]
