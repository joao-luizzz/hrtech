#!/usr/bin/env python
"""
Script para limpar cache Redis de forma segura durante desenvolvimento.

Uso:
    python scripts/clean_cache.py          # Limpa apenas cache aplicação
    python scripts/clean_cache.py --all    # Limpa TUDO do Redis (cache + Celery)
    python scripts/clean_cache.py --verify # Apenas mostra status
"""

import os
import sys
from pathlib import Path

# Adiciona projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrtech.settings')

import django
django.setup()

from django.core.cache import cache
from django.conf import settings
import redis
from decouple import config

def get_redis_connection():
    """Tenta conectar ao Redis se configurado."""
    cache_url = config('CACHE_URL', default='')
    broker_url = config('CELERY_BROKER_URL', default='')
    redis_url = cache_url or broker_url
    
    if not redis_url:
        return None
    
    try:
        # Parse Redis URL e conecta
        r = redis.from_url(redis_url)
        r.ping()
        return r
    except Exception as e:
        print(f"⚠️  Erro ao conectar Redis: {e}")
        return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpa cache do aplicação')
    parser.add_argument('--all', action='store_true', help='Limpa TUDO do Redis (cache + Celery)')
    parser.add_argument('--verify', action='store_true', help='Apenas mostra status')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("GERENCIADOR DE CACHE")
    print("="*70)
    print(f"Ambiente: {settings.ENVIRONMENT.upper()}")
    print(f"Debug: {settings.DEBUG}")
    print(f"Backend de Cache: {type(cache).__name__}")
    
    # Tenta conectar ao Redis
    redis_conn = get_redis_connection()
    
    if redis_conn:
        print(f"✅ Redis CONECTADO")
        try:
            info = redis_conn.info()
            db_size = redis_conn.dbsize()
            print(f"   - Versão: {info['redis_version']}")
            print(f"   - Chaves no DB: {db_size}")
        except Exception as e:
            print(f"   ⚠️  Erro ao obter info: {e}")
    else:
        print(f"🟡 Redis NÃO configurado (usando LocMemCache em memória)")
    
    print()
    
    if args.verify:
        print("📊 Status verificado. Nenhuma ação executada.")
        return
    
    if not redis_conn:
        print("❌ Redis não está configurado/conectável")
        print("   Use em .env: CACHE_URL=redis://localhost:6379/1")
        print("   Ou: CELERY_BROKER_URL=redis://localhost:6379/0")
        return
    
    # Confirmação antes de limpar
    if args.all:
        print("⚠️  AVISO: Isso vai limpar TUDO do Redis (cache + Celery tasks em espera)")
        confirm = input("Tem certeza? Digite 'sim' para confirmar: ").strip().lower()
        if confirm != 'sim':
            print("❌ Operação cancelada")
            return
        
        try:
            redis_conn.flushall()
            print("✅ TUDO limpo do Redis (FLUSHALL)")
        except Exception as e:
            print(f"❌ Erro ao limpar Redis: {e}")
            return
    else:
        # Limpa apenas cache da aplicação (não Celery)
        try:
            # Django cache clear
            cache.clear()
            
            # Também remove chaves com prefix da app
            pattern = f"hrtech-{settings.ENVIRONMENT}:*"
            keys = redis_conn.keys(pattern)
            if keys:
                redis_conn.delete(*keys)
                print(f"✅ Cache limpado ({len(keys)} chaves removidas)")
            else:
                print(f"✅ Cache já estava vazio")
                
        except Exception as e:
            print(f"❌ Erro ao limpar cache: {e}")
            return
    
    print("\n" + "="*70)
    print("✨ Pronto! Recarregue a página no navegador (Ctrl+Shift+R)")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
