"""
Migration para criar/corrigir usuário RH definitivo.
Corrige problemas de email e garante que o usuário funcione com allauth.
"""
from django.db import migrations
from django.contrib.auth.hashers import make_password


def criar_usuario_rh_definitivo(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('core', 'Profile')
    Site = apps.get_model('sites', 'Site')

    # Credenciais DEFINITIVAS
    EMAIL = 'admin@hrtech.com'
    USERNAME = 'admin@hrtech.com'  # Mesmo que email para evitar confusão
    SENHA = 'Admin123!'

    # Remove usuários antigos que podem estar causando conflito
    User.objects.filter(username__in=['admin_rh', 'rh_admin', 'rh@empresa.com', 'rh@hrtech.com']).delete()
    User.objects.filter(email__in=['rh@empresa.com', 'rh@hrtech.com', 'admin@hrtech.com']).delete()

    # Cria usuário novo
    user = User(
        username=USERNAME,
        email=EMAIL,
        password=make_password(SENHA),
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    user.save()
    print(f'✅ Usuário criado: {EMAIL} / {SENHA}')

    # Cria Profile com role RH
    Profile.objects.filter(user=user).delete()  # Remove profile antigo se existir
    Profile.objects.create(user=user, role='rh')
    print('✅ Profile RH criado!')

    # Configura Site
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': 'hrtech-h64w.onrender.com',
            'name': 'HRTech ATS'
        }
    )
    print('✅ Site configurado!')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_resetar_senha_rh'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(criar_usuario_rh_definitivo, migrations.RunPython.noop),
    ]
