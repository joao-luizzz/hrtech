from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Configura o utilizador inicial do RH e o domínio do Site para produção'

    def handle(self, *args, **kwargs):
        # 0. VARIÁVEIS DE CONFIGURAÇÃO (Altere aqui se necessário)
        email = 'rh@empresa.com'
        username = 'admin_rh'
        password = 'SuaSenhaSegura123!'
        domain = 'hrtech-h64w.onrender.com' # <-- SUBSTITUA PELO SEU LINK DO RENDER

        # 1. CRIAR O UTILIZADOR SUPERADMIN
        # Verifica se o utilizador já existe para não dar erro em futuros deploys
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_superuser(username, email, password)
            self.stdout.write(self.style.SUCCESS(f'✅ Utilizador {username} criado com sucesso!'))
        else:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(f'⚠️ Utilizador {username} já existe. Ignorando criação.'))

        # 2. CONFIGURAR O PERFIL (Role-Based Access Control)
        # Associa o utilizador recém-criado à função 'rh'
        profile, created = Profile.objects.get_or_create(user=user)
        profile.role = 'rh'
        profile.save()
        self.stdout.write(self.style.SUCCESS('✅ Perfil de RH configurado com sucesso!'))

        # 3. CONFIGURAR O DOMÍNIO DO ALLAUTH (Para links de E-mail)
        # O ID 1 é o site padrão que o Django cria; vamos apenas atualizá-lo
        site, created = Site.objects.get_or_create(id=1)
        site.domain = domain
        site.name = 'HRTech ATS'
        site.save()
        self.stdout.write(self.style.SUCCESS(f'✅ Domínio do site configurado para {domain}'))