FROM python:3.11-slim

# Argumentos de build
ARG DEBIAN_FRONTEND=noninteractive
ARG APP_HOME=/app

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV TZ=America/Sao_Paulo

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    tzdata \
    curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório da aplicação
WORKDIR $APP_HOME

# Copiar arquivos de requisitos primeiro (para cache de camadas)
COPY requirements.txt .

# Instalar requisitos Python
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir tomli # Para gerar_requirements.py

# Copiar o código da aplicação
COPY . .

# Criar diretório para backups e logs
RUN mkdir -p backups logs

# Dar permissão de execução ao script de entrada
RUN chmod +x docker-entrypoint.sh

# Verificação de saúde
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Expor a porta 5000
EXPOSE 5000

# Usar o script de entrada como ponto de entrada
ENTRYPOINT ["./docker-entrypoint.sh"]

# Comando de execução padrão
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "--access-logfile", "logs/access.log", "--error-logfile", "logs/error.log", "main:app"]