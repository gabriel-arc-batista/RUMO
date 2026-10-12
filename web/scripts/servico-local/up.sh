#!/usr/bin/env bash
# Supabase mínimo e descartável para validar o site: Postgres 17.6 + GoTrue + PostgREST
# + nginx como gateway (/auth/v1, /rest/v1, CORS). Só loopback, dados sintéticos.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd)
OUT="$S/.tmp"; mkdir -p "$OUT"
ROOT=$(cd "$S/../../.." && pwd)
NET=rumo-webtest
SECRET=rumo-disposable-web-test-secret-32-bytes-long
docker network create $NET >/dev/null 2>&1 || true
docker rm -f rumo-webtest-db rumo-webtest-auth rumo-webtest-rest rumo-webtest-gw rumo-webtest-mail >/dev/null 2>&1 || true
# MAIL=1: e-mail real de teste (Mailpit) para confirmação de cadastro e recuperação de senha.
MAIL_ENV=(-e GOTRUE_MAILER_AUTOCONFIRM=true)
if [ "${MAIL:-0}" = "1" ]; then
  docker run -d --name rumo-webtest-mail --network $NET -p 127.0.0.1:8025:8025 axllent/mailpit:v1.27.0 >/dev/null
  MAIL_ENV=(-e GOTRUE_MAILER_AUTOCONFIRM=false -e GOTRUE_SMTP_HOST=rumo-webtest-mail -e GOTRUE_SMTP_PORT=1025
    -e GOTRUE_SMTP_USER=teste -e GOTRUE_SMTP_PASS=teste -e GOTRUE_SMTP_ADMIN_EMAIL=nao-responda@example.invalid
    -e GOTRUE_SMTP_SENDER_NAME=RUMO -e GOTRUE_MAILER_URLPATHS_CONFIRMATION=/auth/v1/verify
    -e GOTRUE_MAILER_URLPATHS_RECOVERY=/auth/v1/verify -e GOTRUE_RATE_LIMIT_EMAIL_SENT=1000)
fi

docker run -d --name rumo-webtest-db --network $NET -e POSTGRES_PASSWORD=temporary-test-only postgres:17.6 >/dev/null
for i in $(seq 60); do docker exec rumo-webtest-db pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
sql() { docker exec -i rumo-webtest-db psql -U postgres -v ON_ERROR_STOP=1 -q "$@"; }
sed 's/create table auth.users(id uuid primary key);//' "$ROOT/backend/tests/bootstrap.sql" | sql

docker run -d --name rumo-webtest-auth --network $NET \
  -e GOTRUE_API_HOST=0.0.0.0 -e GOTRUE_API_PORT=9999 \
  -e API_EXTERNAL_URL=http://localhost:54321/auth/v1 -e GOTRUE_SITE_URL=http://localhost:4175 \
  -e GOTRUE_URI_ALLOW_LIST="http://localhost:4175/**" \
  -e GOTRUE_DB_DRIVER=postgres \
  -e "GOTRUE_DB_DATABASE_URL=postgres://postgres:temporary-test-only@rumo-webtest-db:5432/postgres?search_path=auth" \
  -e GOTRUE_DB_NAMESPACE=auth -e GOTRUE_JWT_SECRET=$SECRET -e GOTRUE_JWT_AUD=authenticated \
  -e GOTRUE_JWT_DEFAULT_GROUP_NAME=authenticated -e GOTRUE_JWT_ADMIN_ROLES=service_role \
  -e GOTRUE_EXTERNAL_EMAIL_ENABLED=true "${MAIL_ENV[@]}" -e GOTRUE_DISABLE_SIGNUP=false \
  supabase/gotrue:v2.177.0 >/dev/null
for i in $(seq 60); do docker exec rumo-webtest-db psql -U postgres -tAc "select to_regclass('auth.users')" | grep -q users && break; sleep 1; done

for m in "$ROOT"/backend/migrations/*.sql; do sql < "$m"; done
# Seed a partir do catálogo de EXEMPLO do site (rolldown já vem com o Vite).
"$S/../../node_modules/.bin/rolldown" "$S/../../src/service/example/catalog.ts" --platform node --format esm --file "$OUT/catalog.mjs" >/dev/null
node "$S/seed.mjs" http://localhost:4175 > "$OUT/seed.sql"
[ "${SEED:-1}" = "0" ] || sql < "$OUT/seed.sql"

docker run -d --name rumo-webtest-rest --network $NET \
  -e PGRST_DB_URI=postgres://postgres:temporary-test-only@rumo-webtest-db:5432/postgres \
  -e PGRST_DB_SCHEMAS=public -e PGRST_DB_ANON_ROLE=anon -e PGRST_JWT_SECRET=$SECRET \
  postgrest/postgrest:v14.2 >/dev/null

cat > "$OUT/nginx.conf" <<'NGINX'
events {}
http {
  server {
    listen 54321;
    location / {
      if ($request_method = OPTIONS) {
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Headers "authorization,apikey,content-type,x-client-info,accept-profile,content-profile,prefer,x-supabase-api-version" always;
        add_header Access-Control-Allow-Methods "GET,POST,PATCH,PUT,DELETE,OPTIONS" always;
        add_header Access-Control-Max-Age 600 always;
        return 204;
      }
      add_header Access-Control-Allow-Origin $http_origin always;
      add_header Access-Control-Expose-Headers "content-range,x-total-count" always;
      return 404;
    }
    location /auth/v1/ {
      if ($request_method = OPTIONS) {
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Headers "authorization,apikey,content-type,x-client-info,x-supabase-api-version" always;
        add_header Access-Control-Allow-Methods "GET,POST,PUT,DELETE,OPTIONS" always;
        return 204;
      }
      proxy_hide_header Access-Control-Allow-Origin;
      proxy_hide_header Access-Control-Allow-Credentials;
      add_header Access-Control-Allow-Origin $http_origin always;
      proxy_pass http://rumo-webtest-auth:9999/;
    }
    location /rest/v1/ {
      if ($request_method = OPTIONS) {
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Headers "authorization,apikey,content-type,x-client-info,accept-profile,content-profile,prefer,x-supabase-api-version" always;
        add_header Access-Control-Allow-Methods "GET,POST,PATCH,PUT,DELETE,OPTIONS" always;
        return 204;
      }
      proxy_hide_header Access-Control-Allow-Origin;
      add_header Access-Control-Allow-Origin $http_origin always;
      add_header Access-Control-Expose-Headers "content-range,x-total-count" always;
      proxy_pass http://rumo-webtest-rest:3000/;
    }
  }
}
NGINX
docker run -d --name rumo-webtest-gw --network $NET -p 127.0.0.1:54321:54321 \
  -v "$OUT/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:1.29-alpine >/dev/null

# Chave pública "anon" assinada com o segredo descartável (equivalente à anon key).
ANON=$(python3 - "$SECRET" <<'PY'
import base64, hashlib, hmac, json, sys, time
enc = lambda v: base64.urlsafe_b64encode(json.dumps(v, separators=(",", ":")).encode()).decode().rstrip("=")
body = enc({"alg": "HS256", "typ": "JWT"}) + "." + enc({"role": "anon", "iss": "rumo-webtest", "exp": int(time.time()) + 86400})
sig = base64.urlsafe_b64encode(hmac.new(sys.argv[1].encode(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
print(body + "." + sig)
PY
)
printf 'VITE_SUPABASE_URL=http://localhost:54321\nVITE_SUPABASE_ANON_KEY=%s\n' "$ANON" > "$OUT/env.servico"
for i in $(seq 30); do curl -sf http://localhost:54321/auth/v1/health >/dev/null && break; sleep 1; done
curl -s http://localhost:54321/auth/v1/health; echo
cp "$OUT/env.servico" "$S/../../.env.servico.local"
echo "pilha pronta: gateway http://localhost:54321 (configuração em web/.env.servico.local)"
