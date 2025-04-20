# Implantação com Docker

Este documento fornece instruções rápidas para implantar o Sistema de Gestão Agropecuária usando Docker e Docker Compose.

## Requisitos

- Docker instalado (versão 20.10+)
- Docker Compose instalado (versão 2.0+)

## Passo a Passo

### 1. Prepare o ambiente

Clone o repositório ou baixe todos os arquivos do sistema:

```bash
git clone https://seu-repositorio.git
cd sistema-agropecuario
```

### 2. Prepare o arquivo requirements.txt

```bash
python gerar_requirements.py
```

### 3. Implante com Docker Compose

```bash
# Construir e iniciar os contêineres
docker-compose up -d

# Verificar se os contêineres estão rodando
docker-compose ps
```

### 4. Inicializar o banco de dados (apenas primeira vez)

```bash
# Executar a migração do banco de dados
docker-compose exec web python -c "from app import app; from models import db; app.app_context().push(); db.create_all()"

# Criar dados de exemplo (opcional)
docker-compose exec web python criar_estacoes_exemplo_rotas.py
```

### 5. Acesse o sistema

O sistema estará disponível em: http://localhost:5000

## Comandos Úteis

### Visualizar logs
```bash
docker-compose logs -f
```

### Reiniciar serviços
```bash
docker-compose restart
```

### Parar serviços
```bash
docker-compose down
```

### Atualizar após mudanças no código
```bash
docker-compose build web
docker-compose up -d
```

## Configuração para Produção

Para uso em produção, é altamente recomendado:

1. Modificar as senhas e variáveis no arquivo `docker-compose.yml`
2. Configurar um proxy reverso (Nginx/Traefik) para HTTPS
3. Montar os volumes em locais seguros para backup

## Para Mais Detalhes

Consulte a documentação completa em [docs/instalacao_docker.md](docs/instalacao_docker.md)