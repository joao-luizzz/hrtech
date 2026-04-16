#!/bin/bash
# Script rápido para limpar cache Redis + hard refresh no navegador
# 
# Uso:
#   ./scripts/quick_cache_clean.sh          # Limpa cache + instruções
#   ./scripts/quick_cache_clean.sh --verify  # Apenas status

set -e

ENVIRONMENT=${ENVIRONMENT:-development}
DEBUG=${DEBUG:-True}

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                  GERENCIADOR RÁPIDO DE CACHE                       ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Ambiente: $ENVIRONMENT"
echo "Debug: $DEBUG"
echo ""

# Verifica se Redis está rodando
if command -v redis-cli &> /dev/null; then
    echo "🔍 Testando Redis..."
    
    if redis-cli ping > /dev/null 2>&1; then
        REDIS_OK=true
        DB_SIZE=$(redis-cli DBSIZE | awk '{print $2}')
        echo "✅ Redis CONECTADO (chaves: $DB_SIZE)"
    else
        REDIS_OK=false
        echo "❌ Redis não responde (está rodando?)"
    fi
else
    echo "⚠️  redis-cli não encontrado"
    REDIS_OK=false
fi

echo ""

# Verifica argumentos
if [[ "$1" == "--verify" ]]; then
    echo "✅ Status verificado. Nenhuma ação executada."
    exit 0
fi

# Se Redis não está ok, apenas mostra aviso
if [[ "$REDIS_OK" == "false" ]]; then
    echo "ℹ️  Redis não está disponível"
    echo ""
    echo "Para Redis local, instale:"
    echo "  sudo apt install redis-server   # Ubuntu/Debian"
    echo "  brew install redis             # Mac"
    echo ""
    echo "Ou configure em .env: CACHE_URL=redis://localhost:6379/1"
    echo ""
    exit 0
fi

# Limpa cache
echo "🧹 Limpando cache do Redis..."
redis-cli FLUSHALL > /dev/null

echo "✅ Cache limpo!"
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  PRÓXIMOS PASSOS:                                                  ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║  1. Abra o navegador (já na página)                                ║"
echo "║  2. Limpe cache do navegador:                                      ║"
echo "║     - Windows/Linux: Ctrl + Shift + R                              ║"
echo "║     - Mac: Cmd + Shift + R                                         ║"
echo "║  3. Recarregue (F5 simples)                                        ║"
echo "║                                                                    ║"
echo "║  Suas mudanças devem aparecer agora! ✨                            ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
