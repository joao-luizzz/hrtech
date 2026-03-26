"""
Migration para criar usuário RH inicial e configurar Site.
Roda automaticamente no deploy.
"""
import os

from django.db import migrations


def criar_usuario_rh(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('core', 'Profile')
    Site = apps.get_model('sites', 'Site')

    # Configurações do usuário RH lidas de variáveis de ambiente
    EMAIL = os.getenv('RH_ADMIN_EMAIL', 'rh@empresa.com')
    USERNAME = os.getenv('RH_ADMIN_USERNAME', 'admin_rh')
    PASSWORD = os.getenv('RH_ADMIN_PASSWORD')
    DOMAIN = os.getenv('SITE_DOMAIN', 'localhost')

    # Cria usuário se não existir
    if not User.objects.filter(username=USERNAME).exists():
        if not PASSWORD:
            print('⚠️ RH_ADMIN_PASSWORD não definido. Usuário RH não foi criado.')
        else:
            user = User.objects.create_superuser(
                username=USERNAME,
                email=EMAIL,
                password=PASSWORD
            )
            # Cria Profile com role RH
            Profile.objects.create(user=user, role='rh')
            print('✅ Usuário RH criado com perfil RH!')
    else:
        user = User.objects.get(username=USERNAME)
        # Garante que o profile existe
        Profile.objects.get_or_create(user=user, defaults={'role': 'rh'})
        print(f'⚠️ Usuário {USERNAME} já existe.')

    # Configura Site para allauth
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': DOMAIN,
            'name': 'HRTech ATS'
        }
    )
    print('✅ Site configurado!')


def reverter(apps, schema_editor):
    pass  # Não reverte usuário


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_candidato_etapa_processo_profile_historicoacao'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(criar_usuario_rh, reverter),
    ]
