#!/usr/bin/env bash
# Remove a pilha local descartável (nenhum dado pessoal é usado nela).
docker rm -f rumo-webtest-db rumo-webtest-auth rumo-webtest-rest rumo-webtest-gw rumo-webtest-mail >/dev/null 2>&1 || true
docker network rm rumo-webtest >/dev/null 2>&1 || true
echo "pilha local removida"
