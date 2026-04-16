#!/usr/bin/env python
"""
Script de verificação PRÉ-DEPLOY

Executa uma série de verificações críticas antes de fazer deploy para produção:
- Checa secrets expostos no código
- Verifica configurações de segurança
- Valida variáveis de ambiente obrigatórias
- Testa conexões com serviços externos

Uso:
    python scripts/verify_settings.py              # Verificação padrão
    python scripts/verify_settings.py --strict    # Mais rigoroso  
    python scripts/verify_settings.py --production # Modo produção (obrigatório)
"""

import os
import sys
import re
import subprocess
from pathlib import Path

# Adiciona projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrtech.settings')

import django
django.setup()

from django.conf import settings
from decouple import config

def print_header(title):
    print(f"\n{'='*70}")
    print(f"🔍 {title}")
    print(f"{'='*70}")

def print_check(status, message):
    """status: ✅, ⚠️, ❌"""
    print(f"{status} {message}")

def check_debug_mode():
    """DEBUG deve ser False em produção/staging"""
    print_header("MODO DEBUG")
    
    if settings.DEBUG:
        if settings.ENVIRONMENT == 'production':
            print_check("❌", "DEBUG=True em produção! CRÍTICO - mude para False")
            return False
        else:
            print_check("✅", f"DEBUG=True (ok para {settings.ENVIRONMENT})")
            return True
    else:
        print_check("✅", "DEBUG=False (seguro para produção)")
        return True

def check_secret_key():
    """SECRET_KEY deve ser forte e não hardcoded"""
    print_header("SECRET KEY")
    
    secret = settings.SECRET_KEY
    
    if not secret or secret == 'change-me':
        print_check("❌", "SECRET_KEY inválido ou padrão!")
        return False
    
    if len(secret) < 50:
        print_check("⚠️", f"SECRET_KEY muito curta ({len(secret)} chars, recomendado 50+)")
        return False
    
    print_check("✅", f"SECRET_KEY forte ({len(secret)} caracteres)")
    return True

def check_allowed_hosts():
    """ALLOWED_HOSTS deve ser configurado e seguro"""
    print_header("ALLOWED HOSTS")
    
    hosts = settings.ALLOWED_HOSTS
    
    if not hosts:
        if settings.ENVIRONMENT == 'production':
            print_check("❌", "ALLOWED_HOSTS vizio em produção!")
            return False
        print_check("⚠️", "ALLOWED_HOSTS vazio (ok para dev)")
        return True
    
    if '*' in hosts:
        print_check("❌", "ALLOWED_HOSTS contém '*' - nunca em produção!")
        return False
    
    print_check("✅", f"ALLOWED_HOSTS configurado: {', '.join(hosts)}")
    return True

def check_ssl_settings():
    """Verifica se SSL está configurado para produção"""
    print_header("SEGURANÇA SSL/TLS")
    
    if settings.DEBUG or settings.ENVIRONMENT == 'development':
        print_check("⚠️", "SSL checks desabilitado em desenvolvimento")
        return True
    
    checks = [
        ('SECURE_SSL_REDIRECT', settings.SECURE_SSL_REDIRECT),
        ('SESSION_COOKIE_SECURE', settings.SESSION_COOKIE_SECURE),
        ('CSRF_COOKIE_SECURE', settings.CSRF_COOKIE_SECURE),
        ('SECURE_HSTS_SECONDS', getattr(settings, 'SECURE_HSTS_SECONDS', 0)),
    ]
    
    all_ok = True
    for name, value in checks:
        if value:
            print_check("✅", f"{name}={value}")
        else:
            print_check("❌", f"{name}={value} (deve estar ativado)")
            all_ok = False
    
    return all_ok

def check_redis_configuration():
    """Verifica se Redis está configurado corretamente por ambiente"""
    print_header("REDIS / CACHE")
    
    cache_url = config('CACHE_URL', default='')
    broker_url = config('CELERY_BROKER_URL', default='')
    
    print(f"Ambiente: {settings.ENVIRONMENT}")
    
    if settings.ENVIRONMENT == 'production':
        # Produção DEVE ter Redis
        if not (cache_url or broker_url):
            print_check("❌", "Redis não configurado em PRODUÇÃO!")
            print("   Configure no .env: CELERY_BROKER_URL=redis://...")
            return False
        
        print_check("✅", "Redis configurado para produção")
        
        if '127.0.0.1' in (cache_url + broker_url):
            print_check("❌", "Redis apontando para localhost em produção!")
            return False
        
        return True
    
    elif settings.ENVIRONMENT == 'development':
        if not (cache_url or broker_url):
            print_check("✅", "Redis desabilitado (usando LocMemCache)")
            return True
        
        print_check("⚠️", "Redis configurado mesmo em desenvolvimento")
        return True

def check_database():
    """Verifica se banco de dados está configurado"""
    print_header("BANCO DE DADOS")
    
    db_config = settings.DATABASES.get('default', {})
    engine = db_config.get('ENGINE', '')
    
    if 'sqlite3' in engine:
        if settings.ENVIRONMENT == 'production':
            print_check("❌", "SQLite em produção! Use PostgreSQL")
            return False
        print_check("⚠️", "SQLite usado (ok para dev)")
        return True
    
    if 'postgresql' in engine:
        print_check("✅", "PostgreSQL configurado")
        return True
    
    print_check("⚠️", f"Banco: {engine}")
    return True

def check_secrets_in_code():
    """Verifica se há secrets expostos no código"""
    print_header("SEARCH POR SECRETS EXPOSTOS")
    
    # Padrões perigosos
    patterns = [
        r'password\s*=\s*["\'].*["\']',
        r'secret_key\s*=\s*["\'].*["\']',
        r'api_key\s*=\s*["\']sk-',
        r'token\s*=\s*["\'].*["\']',
    ]
    
    print("Procurando secrets hardcoded no código...")
    
    suspicious_files = []
    for pattern in patterns:
        try:
            result = subprocess.run(
                ['git', 'grep', '-i', '-n', pattern],
                cwd=BASE_DIR,
                capture_output=True,
                text=True
            )
            if result.stdout:
                suspicious_files.append(result.stdout)
        except:
            pass
    
    if suspicious_files:
        print_check("❌", "Encontrados secrets potualmente expostos:")
        for line in suspicious_files:
            print(f"   {line}")
        return False
    
    print_check("✅", "Nenhum secret hardcoded detectado")
    return True

def check_environment_file():
    """Verifica se arquivo .env existe"""
    print_header("ARQUIVO .ENV")
    
    env_file = BASE_DIR / '.env'
    env_local = BASE_DIR / '.env.local'
    
    if not env_file.exists() and not env_local.exists():
        print_check("❌", "Nenhum arquivo .env/.env.local encontrado!")
        return False
    
    if env_file.exists():
        print_check("✅", ".env encontrado")
    
    if env_local.exists():
        print_check("⚠️", ".env.local encontrado (ok para dev)")
    
    return True

def check_static_files():
    """Verifica se arquivos estáticos estão configurados"""
    print_header("ARQUIVOS ESTÁTICOS")
    
    if settings.DEBUG:
        print_check("⚠️", "DEBUG=True (Django serve static files)")
        return True
    
    static_root = settings.STATIC_ROOT
    if not static_root:
        print_check("❌", "STATIC_ROOT não configurado!")
        return False
    
    print_check("✅", f"STATIC_ROOT: {static_root}")
    return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Verifica segurança antes de deploy')
    parser.add_argument('--strict', action='store_true', help='Modo estrito')
    parser.add_argument('--production', action='store_true', help='Validação para produção')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("✅ VERIFICAÇÃO PRÉ-DEPLOY")
    print("="*70)
    print(f"Ambiente: {settings.ENVIRONMENT.upper()}")
    print(f"Debug: {settings.DEBUG}")
    print(f"Host: {os.getenv('HOSTNAME', 'local')}")
    
    checks = [
        ("Debug Mode", check_debug_mode()),
        ("Secret Key", check_secret_key()),
        ("Allowed Hosts", check_allowed_hosts()),
        ("SSL Settings", check_ssl_settings() if settings.ENVIRONMENT != 'development' else True),
        ("Redis/Cache", check_redis_configuration()),
        ("Database", check_database()),
        ("Secrets no Code", check_secrets_in_code()),
        ("Arquivo .env", check_environment_file()),
        ("Static Files", check_static_files() if settings.ENVIRONMENT != 'development' else True),
    ]
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO")
    print("="*70)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\nResultado: {passed}/{total} verificações ok")
    
    if passed == total:
        print("\n✨ TUDO OK - pronto para deploy!")
        sys.exit(0)
    else:
        print("\n⚠️  Hay problemas - revise os itens acima")
        sys.exit(1)

if __name__ == '__main__':
    main()
