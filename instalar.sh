#!/bin/bash
# Instalador para Sistema de Gestão Agropecuária no CyberPanel
# Uso: curl -s https://raw.githubusercontent.com/seu-usuario/sistema-gestao-agropecuaria/main/instalar.sh | bash
#      ou
#      wget -qO- https://raw.githubusercontent.com/seu-usuario/sistema-gestao-agropecuaria/main/instalar.sh | bash

# Cores
vermelho='\033[0;31m'
verde='\033[0;32m'
amarelo='\033[0;33m'
azul='\033[0;34m'
reset='\033[0m'

# Banner
echo -e "${verde}"
echo "  _____  _    _ _____            _      _______     _______ "
echo " |  __ \\| |  | |  __ \\     /\\   | |    / ____\\ \\   / / ____|"
echo " | |__) | |  | | |__) |   /  \\  | |   | (___  \\ \\_/ / (___  "
echo " |  _  /| |  | |  _  /   / /\\ \\ | |    \\___ \\  \\   / \\___ \\ "
echo " | | \\ \\| |__| | | \\ \\  / ____ \\| |________) |  | |  ____) |"
echo " |_|  \\_\\\\____/|_|  \\_\\/_/    \\_\\______|_____/   |_| |_____/ "
echo -e "${azul}=== INSTALADOR RÁPIDO - SISTEMA DE GESTÃO AGROPECUÁRIA ===${reset}"
echo -e "${amarelo}RuralSys Inovação Tecnológica${reset}\n"

# Detecta ambiente
echo -e "${azul}Verificando ambiente...${reset}"

# Verifica se está no CyberPanel
if [ ! -d "/usr/local/CyberCP" ]; then
    echo -e "${amarelo}Aviso: Este servidor parece não ter o CyberPanel instalado.${reset}"
    echo -e "${amarelo}O script continuará, mas algumas funcionalidades específicas do CyberPanel não estarão disponíveis.${reset}"
fi

# Verifica requisitos
echo -e "${azul}Verificando requisitos...${reset}"

# Python
if ! command -v python3 &>/dev/null; then
    echo -e "${vermelho}Erro: Python 3 não encontrado. Por favor, instale o Python 3.${reset}"
    exit 1
fi
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "Python: ${verde}$python_version${reset}"

# PostgreSQL
if ! command -v psql &>/dev/null; then
    echo -e "${amarelo}Aviso: PostgreSQL não encontrado. Será necessário configurar manualmente.${reset}"
    has_postgres=false
else
    psql_version=$(psql --version 2>&1 | head -1)
    echo -e "PostgreSQL: ${verde}$psql_version${reset}"
    has_postgres=true
fi

# Diretório atual
current_dir=$(pwd)
echo -e "Diretório de instalação: ${verde}$current_dir${reset}"

# Diretório de domínio no CyberPanel
if [[ "$current_dir" == *"public_html"* ]]; then
    domain_path=${current_dir%/public_html*}
    domain_name=$(basename "$domain_path")
    echo -e "Domínio detectado: ${verde}$domain_name${reset}"
    is_public_html=true
else
    echo -e "${amarelo}Aviso: Não foi possível detectar um domínio do CyberPanel.${reset}"
    is_public_html=false
fi

# Configuração do banco de dados
db_name="fazenda"
db_user="fazenda"
db_password=$(< /dev/urandom tr -dc 'A-Za-z0-9!#$%&' | head -c 12)

# Confirmação
echo -e "\n${amarelo}Configuração do banco de dados:${reset}"
echo "Nome do banco: $db_name"
echo "Usuário: $db_user"
echo "Senha: $db_password"
echo -e "\n${amarelo}Esta instalação irá:${reset}"
echo "1. Baixar o sistema do repositório"
echo "2. Criar um ambiente virtual Python"
echo "3. Instalar todas as dependências"
echo "4. Configurar o banco de dados PostgreSQL"
echo "5. Configurar o arquivo .env"
echo "6. Inicializar o sistema"
echo "7. Criar um serviço para execução contínua"
echo ""

read -p "Deseja continuar? (s/n): " confirm
if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
    echo -e "${vermelho}Instalação cancelada pelo usuário.${reset}"
    exit 1
fi

# Diretório temporário
temp_dir=$(mktemp -d)
echo -e "\n${azul}Baixando o sistema...${reset}"

# Verifica se o git está instalado
if ! command -v git &>/dev/null; then
    echo -e "${amarelo}Git não encontrado. Tentando usar wget/curl...${reset}"
    
    # Tenta usar wget ou curl
    if command -v wget &>/dev/null; then
        echo "Usando wget para baixar..."
        wget -q -O $temp_dir/sistema.zip https://github.com/seu-usuario/sistema-gestao-agropecuaria/archive/main.zip
    elif command -v curl &>/dev/null; then
        echo "Usando curl para baixar..."
        curl -s -L -o $temp_dir/sistema.zip https://github.com/seu-usuario/sistema-gestao-agropecuaria/archive/main.zip
    else
        echo -e "${vermelho}Erro: Não foi possível encontrar git, wget ou curl para baixar o sistema.${reset}"
        exit 1
    fi
    
    # Descompacta o arquivo
    if command -v unzip &>/dev/null; then
        unzip -q $temp_dir/sistema.zip -d $temp_dir
        # Move os arquivos para o diretório atual
        mv $temp_dir/sistema-gestao-agropecuaria-main/* .
    else
        echo -e "${vermelho}Erro: Não foi possível encontrar unzip para extrair o sistema.${reset}"
        exit 1
    fi
else
    echo "Usando git para clonar o repositório..."
    git clone --depth=1 https://github.com/seu-usuario/sistema-gestao-agropecuaria.git $temp_dir/sistema
    # Move os arquivos para o diretório atual
    mv $temp_dir/sistema/* .
fi

# Limpa o diretório temporário
rm -rf $temp_dir

# Cria ambiente virtual Python
echo -e "\n${azul}Criando ambiente virtual Python...${reset}"
python3 -m venv venv

# Ativa o ambiente virtual
source venv/bin/activate

# Instala as dependências
echo -e "\n${azul}Instalando dependências...${reset}"
pip install --upgrade pip
pip install flask flask-login flask-sqlalchemy flask-wtf gunicorn psycopg2-binary werkzeug pandas xlsxwriter email-validator

# Configura o banco de dados PostgreSQL
if [ "$has_postgres" = true ]; then
    echo -e "\n${azul}Configurando banco de dados PostgreSQL...${reset}"
    
    # Verifica se o usuário já existe
    user_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$db_user'")
    
    if [ -z "$user_exists" ]; then
        echo "Criando usuário $db_user..."
        sudo -u postgres psql -c "CREATE USER $db_user WITH PASSWORD '$db_password';"
    fi
    
    # Verifica se o banco de dados já existe
    db_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$db_name'")
    
    if [ -z "$db_exists" ]; then
        echo "Criando banco de dados $db_name..."
        sudo -u postgres psql -c "CREATE DATABASE $db_name OWNER $db_user;"
    fi
    
    echo -e "${verde}Banco de dados configurado com sucesso.${reset}"
else
    echo -e "${amarelo}Aviso: PostgreSQL não está disponível. Configure manualmente o banco de dados.${reset}"
fi

# Cria o arquivo .env
echo -e "\n${azul}Criando arquivo .env...${reset}"
cat > .env << EOF
DATABASE_URL=postgresql://$db_user:$db_password@localhost/$db_name
SESSION_SECRET=$(< /dev/urandom tr -dc 'A-Za-z0-9!#$%&' | head -c 32)
FLASK_APP=main.py
FLASK_ENV=production
EOF

# Inicializa o banco de dados
echo -e "\n${azul}Inicializando banco de dados...${reset}"
cat > init_db_script.py << EOF
from app import app
from main import db
app.app_context().push()
db.create_all()
print("Banco de dados inicializado com sucesso!")
EOF

python init_db_script.py
rm init_db_script.py

# Cria arquivo de configuração do Gunicorn
echo -e "\n${azul}Configurando Gunicorn...${reset}"
cat > gunicorn_conf.py << EOF
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
max_requests = 1000
max_requests_jitter = 50
timeout = 30
EOF

# Se estiver na pasta public_html, configura o .htaccess para proxy
if [ "$is_public_html" = true ]; then
    echo -e "\n${azul}Configurando .htaccess para proxy...${reset}"
    cat > .htaccess << EOF
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(.*)$ http://localhost:5000/$1 [P,L]
</IfModule>
EOF
fi

# Cria arquivo de serviço
echo -e "\n${azul}Criando arquivo de serviço...${reset}"
cat > fazenda.service << EOF
[Unit]
Description=Sistema de Gestão Agropecuária
After=network.target postgresql.service

[Service]
User=$(whoami)
WorkingDirectory=$current_dir
ExecStart=$current_dir/venv/bin/gunicorn --config gunicorn_conf.py main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo -e "${verde}Arquivo de serviço criado: $current_dir/fazenda.service${reset}"
echo "Para instalar o serviço, execute como root:"
echo "  cp $current_dir/fazenda.service /etc/systemd/system/"
echo "  systemctl enable fazenda.service"
echo "  systemctl start fazenda.service"

# Cria README com instruções
echo -e "\n${azul}Criando instruções de acesso...${reset}"
cat > INSTALACAO.md << EOF
# Sistema de Gestão Agropecuária - Instalação Concluída

## Como Acessar o Sistema

1. Se você instalou através do CyberPanel:
   - Acesse pelo seu domínio: https://$domain_name
   - Para inicializar o banco de dados com dados iniciais: https://$domain_name/init_db
   
2. Se você instalou em um servidor dedicado:
   - Certifique-se de que o serviço está em execução: \`systemctl status fazenda.service\`
   - Acesse pelo endereço: http://seu-ip-ou-dominio:5000
   - Para inicializar o banco de dados com dados iniciais: http://seu-ip-ou-dominio:5000/init_db

## Credenciais Padrão

Após inicializar o banco de dados, você pode fazer login com:
- Email: admin@fazenda.com
- Senha: admin

**Importante:** Altere a senha padrão após o primeiro login!

## Documentação

Consulte a pasta \`docs\` para obter informações detalhadas sobre:
- Manual do usuário
- Instalação e configuração
- API para dispositivos LoRa
- Integração com estações meteorológicas

## Suporte

Para suporte técnico, entre em contato:
- Email: suporte@ruralsys.com.br
- Telefone: (11) 1234-5678
- Horário de atendimento: Segunda a Sexta, 8h às 18h

---

© RuralSys Inovação Tecnológica - Todos os direitos reservados
EOF

# Limpa o histórico de comandos
history -c

# Conclusão
echo -e "\n${verde}✓ Instalação concluída com sucesso!${reset}"
echo -e "\n${azul}Instruções para acesso:${reset}"

if [ "$is_public_html" = true ]; then
    echo "1. Acesse pelo seu domínio: https://$domain_name"
    echo "2. Para inicializar o banco de dados com dados iniciais: https://$domain_name/init_db"
else
    echo "1. Inicie o serviço: systemctl start fazenda.service"
    echo "2. Acesse pelo endereço: http://seu-ip:5000"
    echo "3. Para inicializar o banco de dados com dados iniciais: http://seu-ip:5000/init_db"
fi

echo -e "\n${amarelo}Credenciais padrão após inicialização:${reset}"
echo "- Email: admin@fazenda.com"
echo "- Senha: admin"
echo -e "\n${vermelho}IMPORTANTE: Altere a senha padrão após o primeiro login!${reset}"
echo -e "\n${verde}Obrigado por instalar o Sistema de Gestão Agropecuária!${reset}"

# Pergunta se deseja remover o script de instalação
read -p "Deseja remover este script de instalação? (s/n): " remove_script
if [[ "$remove_script" == "s" || "$remove_script" == "S" ]]; then
    echo -e "${amarelo}Removendo script de instalação...${reset}"
    rm -- "$0"
    echo -e "${verde}Script removido.${reset}"
fi