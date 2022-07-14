#!/bin/bash
set -e

SERVER_PORT=${1-5000}
export DATABASE_HOST=localhost
export DATABASE_PORT=15432
export DATABASE_USER=dhos-encounters
export DATABASE_PASSWORD=dhos-encounters
export DATABASE_NAME=dhos-encounters-db
export SERVER_PORT=${SERVER_PORT}
export AUTH0_DOMAIN=https://login-sandbox.sensynehealth.com/
export AUTH0_AUDIENCE=https://dev.sensynehealth.com/
export AUTH0_METADATA=https://gdm.sensynehealth.com/metadata
export AUTH0_JWKS_URL=https://login-sandbox.sensynehealth.com/.well-known/jwks.json
export ENVIRONMENT=DEVELOPMENT
export ALLOW_DROP_DATA=true
export PROXY_URL=http://localhost
export HS_KEY=secret
export FLASK_APP=dhos_encounters_api/autoapp.py
export IGNORE_JWT_VALIDATION=true
export RABBITMQ_DISABLED=true
export REDIS_INSTALLED=False
export LOG_FORMAT=colour
export LOG_LEVEL=DEBUG

scripts/setup_local.sh

if [ -z "$*" ]
then
  python3 -m flask db upgrade
  python3 -m dhos_encounters_api
else
  python3 -m flask "$@"
fi
