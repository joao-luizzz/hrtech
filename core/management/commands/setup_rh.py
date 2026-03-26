import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Configura o utilizador inicial do RH e o domínio do Site para produção'

    def handle(self, *args, **kwargs):
        # 0. Variáveis de configuração via ambiente (sem credenciais hardcoded)
        username = os.getenv('RH_ADMIN_USERNAME', 'admin_rh')
        email = os.getenv('RH_ADMIN_EMAIL', 'rh@empresa.com')
        password = os.getenv('RH_ADMIN_PASSWORD')
        domain = os.getenv('SITE_DOMAIN', '')

        if not domain:
            allowed_hosts = [host for host in settings.ALLOWED_HOSTS if host and host != '*']
            domain = allowed_hosts[0] if allowed_hosts else 'localhost'

        user = None

        # 1. CRIAR O UTILIZADOR SUPERADMIN
        # Verifica se o utilizador já existe para não dar erro em futuros deploys.
        # Se não existir e faltar password no ambiente, não cria automaticamente.
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(f'Utilizador {username} já existe. Ignorando criação.'))
        else:
            if not password:
                self.stdout.write(
                    self.style.WARNING(
                        'RH_ADMIN_PASSWORD não definido. Utilizador admin não foi criado automaticamente.'
                    )
                )
            else:
                user = User.objects.create_superuser(username, email, password)
                self.stdout.write(self.style.SUCCESS(f'Utilizador {username} criado com sucesso.'))

        # 2. CONFIGURAR O PERFIL (Role-Based Access Control)
        # Associa o utilizador recém-criado à função 'rh'.
        if user:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = Profile.Role.RH
            profile.save()
            self.stdout.write(self.style.SUCCESS('Perfil de RH configurado com sucesso.'))

        # 3. CONFIGURAR O DOMÍNIO DO ALLAUTH (Para links de E-mail)
        # O ID 1 é o site padrão que o Django cria; vamos apenas atualizá-lo
        site, _ = Site.objects.get_or_create(id=1)
        site.domain = domain
        site.name = 'HRTech ATS'
        site.save()
        self.stdout.write(self.style.SUCCESS(f'Domínio do site configurado para {domain}'))