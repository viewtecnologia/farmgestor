#!/bin/bash
set -e

# Função para verificar se o banco de dados está disponível
function postgres_ready(){
python << END
import sys
import psycopg2
import os

try:
    dbname = os.environ.get('DATABASE_URL')
    if dbname is None:
        dbname = "postgresql://fazenda:fazenda@db/fazenda"
    conn = psycopg2.connect(dbname)
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
}

# Aguarda o PostgreSQL inicializar
until postgres_ready; do
  >&2 echo "PostgreSQL não está disponível ainda - aguardando..."
  sleep 1
done

>&2 echo "PostgreSQL está disponível - continuando..."

# Inicializa o banco de dados se necessário
python -c "from app import app; from models import db; app.app_context().push(); db.create_all()"

# Carrega dados de exemplo se o ambiente for de desenvolvimento
if [ "$FLASK_ENV" = "development" ]; then
  >&2 echo "Ambiente de desenvolvimento - carregando dados de exemplo..."
  python criar_estacoes_exemplo_rotas.py
fi

# Executa o comando fornecido ou o gunicorn por padrão
exec "$@"