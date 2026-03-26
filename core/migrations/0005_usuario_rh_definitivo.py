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

    # Configuração via ambiente
    EMAIL = os.getenv('RH_ADMIN_EMAIL', 'rh@empresa.com')
    USERNAME = os.getenv('RH_ADMIN_USERNAME', EMAIL)
    SENHA = os.getenv('RH_ADMIN_PASSWORD')
    SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'localhost')

    user = None

    # Cria/atualiza usuário apenas se senha estiver disponível
    if not SENHA:
        print('⚠️ RH_ADMIN_PASSWORD ausente. Criação/atualização de usuário RH ignorada.')
    else:
        user, _ = User.objects.update_or_create(
            username=USERNAME,
            defaults={
                'email': EMAIL,
                'password': make_password(SENHA),
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )
        print('✅ Usuário RH criado/atualizado.')

    # Cria/garante Profile com role RH
    if user:
        Profile.objects.update_or_create(user=user, defaults={'role': 'rh'})
        print('✅ Profile RH criado/atualizado.')

    # Configura Site
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': SITE_DOMAIN,
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
