"""
Migration para criar/corrigir usuário RH definitivo.
Corrige problemas de email e garante que o usuário funcione com allauth.
"""
import os

from django.db import migrations
from django.contrib.auth.hashers import make_password


def criar_usuario_rh_definitivo(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('core', 'Profile')
    Site = apps.get_model('sites', 'Site')

    # Credenciais lidas de variáveis de ambiente
    EMAIL = os.getenv('RH_ADMIN_EMAIL', 'rh@empresa.com')
    USERNAME = os.getenv('RH_ADMIN_USERNAME', EMAIL)
    SENHA = os.getenv('RH_ADMIN_PASSWORD')
    DOMAIN = os.getenv('SITE_DOMAIN', 'localhost')

    if not SENHA:
        print('⚠️ RH_ADMIN_PASSWORD não definido. Usuário RH definitivo não foi criado.')
    else:
        # Remove usuários antigos que podem estar causando conflito
        User.objects.filter(username__in=['admin_rh', 'rh_admin']).delete()

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
        print('✅ Usuário RH criado.')

        # Cria Profile com role RH
        Profile.objects.filter(user=user).delete()  # Remove profile antigo se existir
        Profile.objects.create(user=user, role='rh')
        print('✅ Profile RH criado!')

    # Configura Site
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': DOMAIN,
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
