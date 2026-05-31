#!/bin/bash

# Verifica se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "ERRO: Docker não está rodando. Inicie o Docker e tente novamente."
    exit 1
fi

# Detecta o comando docker compose disponível
if docker compose version > /dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "ERRO: docker compose ou docker-compose não encontrado."
    exit 1
fi

echo "Usando: $COMPOSE"

# Verifica se algum serviço já está em execução
# --status running é a sintaxe correta no Compose v2; -q retorna só os IDs
if $COMPOSE ps --status running --quiet 2>/dev/null | grep -q .; then
    echo "Infraestrutura já está em execução."
    echo ""
    $COMPOSE ps
    exit 0
fi

echo "Subindo a infraestrutura..."
$COMPOSE up -d --build

echo ""
echo "Status dos contêineres:"
$COMPOSE ps

echo ""
echo "Acesso:"
echo "  App (via Nginx): http://localhost"
echo "  Grafana:         http://localhost/grafana/"
