#!/bin/bash
#
# Script de Instalação do RuralSys via FTP
# Para sistemas Ubuntu/Debian
#

# Cores para formatação de texto
VERMELHO='\033[0;31m'
VERDE='\033[0;32m'
AMARELO='\033[0;33m'
AZUL='\033[0;34m'
NEGRITO='\033[1m'
RESET='\033[0m'

# Variáveis globais
USUARIO=$(whoami)
DIRETORIO_INSTALACAO="/opt/ruralsys"
DIRETORIO_TEMP="/tmp/ruralsys_temp"
DIRETORIO_FTP="/home/$USUARIO/ftp_ruralsys"
PORTA_FTP_PASSIVA="21000-21010"
USUARIO_FTP="ruralsys_ftp"
SENHA_FTP="$(openssl rand -base64 12)"  # Senha aleatória para segurança
ARQUIVO_ZIP="ruralsys.zip"
PORTA_APLICACAO="5000"  # Porta padrão, pode ser alterada pelo usuário
PORTA_HTTP="80"         # Porta padrão HTTP

# Verificar se é root
verificar_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${VERMELHO}Este script precisa ser executado como root (sudo).${RESET}"
        echo -e "Por favor, execute: ${NEGRITO}sudo $0${RESET}"
        exit 1
    fi
}

# Função para imprimir cabeçalho
imprimir_cabecalho() {
    clear
    echo -e "${AZUL}${NEGRITO}===========================================================${RESET}"
    echo -e "${AZUL}${NEGRITO}      INSTALADOR DO RURALSYS - SISTEMA DE GESTÃO RURAL    ${RESET}"
    echo -e "${AZUL}${NEGRITO}===========================================================${RESET}"
    echo
}

# Função para imprimir o menu principal
imprimir_menu() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Opções de Instalação:${RESET}"
    echo -e "  ${VERDE}1.${RESET} Verificar requisitos do sistema"
    echo -e "  ${VERDE}2.${RESET} Configurar servidor FTP para upload dos arquivos"
    echo -e "  ${VERDE}3.${RESET} Instalar dependências do sistema"
    echo -e "  ${VERDE}4.${RESET} Instalar e configurar PostgreSQL"
    echo -e "  ${VERDE}5.${RESET} Extrair e instalar o RuralSys"
    echo -e "  ${VERDE}6.${RESET} Configurar serviço systemd"
    echo -e "  ${VERDE}7.${RESET} Configurar portas da aplicação"
    echo -e "  ${VERDE}8.${RESET} Testar a instalação"
    echo -e "  ${VERDE}9.${RESET} Instalação Automática (executa todas as etapas)"
    echo -e "  ${VERDE}10.${RESET} Desinstalar RuralSys"
    echo -e "  ${VERDE}0.${RESET} Sair"
    echo
    echo -e "${NEGRITO}Digite o número da opção desejada:${RESET} "
}

# Verificar requisitos do sistema
verificar_requisitos() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Verificando requisitos do sistema...${RESET}"
    echo
    
    # Verificar versão do Ubuntu
    if [ -f /etc/lsb-release ]; then
        source /etc/lsb-release
        echo -e "Sistema Operacional: ${VERDE}$DISTRIB_DESCRIPTION${RESET}"
    else
        echo -e "${AMARELO}AVISO: Não foi possível identificar a versão do Ubuntu.${RESET}"
        echo -e "Este script foi desenvolvido para Ubuntu 20.04 ou superior."
    fi
    
    # Verificar espaço em disco
    ESPACO_LIVRE=$(df -h / | awk 'NR==2 {print $4}')
    echo -e "Espaço livre em disco: ${VERDE}$ESPACO_LIVRE${RESET}"
    
    # Verificar memória RAM
    MEM_TOTAL=$(free -h | awk 'NR==2 {print $2}')
    echo -e "Memória RAM total: ${VERDE}$MEM_TOTAL${RESET}"
    
    # Verificar se python está instalado
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "Python: ${VERDE}$PYTHON_VERSION${RESET}"
    else
        echo -e "${VERMELHO}Python 3 não está instalado.${RESET}"
        echo -e "O RuralSys requer Python 3.8 ou superior."
    fi
    
    # Verificar se PostgreSQL está instalado
    if command -v psql &>/dev/null; then
        PSQL_VERSION=$(psql --version)
        echo -e "PostgreSQL: ${VERDE}$PSQL_VERSION${RESET}"
    else
        echo -e "${AMARELO}PostgreSQL não está instalado.${RESET}"
        echo -e "Será instalado durante o processo."
    fi
    
    # Verificar conectividade com a internet
    echo "Verificando conexão com a internet..."
    if ping -c 1 google.com &>/dev/null; then
        echo -e "Conexão com a Internet: ${VERDE}OK${RESET}"
    else
        echo -e "${VERMELHO}Sem conexão com a Internet.${RESET}"
        echo -e "Uma conexão ativa é necessária para baixar dependências."
    fi
    
    echo
    echo -e "Requisitos mínimos para o RuralSys:"
    echo -e " - Ubuntu 20.04 ou superior"
    echo -e " - 2GB de RAM"
    echo -e " - 5GB de espaço em disco"
    echo -e " - Python 3.8+"
    echo -e " - PostgreSQL 12+"
    echo
    
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Configurar servidor FTP para upload
configurar_ftp() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Configurando servidor FTP para upload dos arquivos${RESET}"
    echo
    
    echo "Esta etapa irá configurar um servidor FTP para você fazer upload do arquivo ZIP do RuralSys."
    echo -e "${AMARELO}ATENÇÃO: Você precisará fazer upload do arquivo $ARQUIVO_ZIP via FTP depois.${RESET}"
    echo
    
    read -p "Deseja continuar com a configuração do servidor FTP? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Configuração do servidor FTP abortada."
        return
    fi
    
    echo
    echo -e "${NEGRITO}Instalando servidor vsftpd...${RESET}"
    apt-get update
    apt-get install -y vsftpd
    
    # Backup da configuração original
    if [ -f /etc/vsftpd.conf ]; then
        cp /etc/vsftpd.conf /etc/vsftpd.conf.bak
        echo "Backup da configuração original criado em /etc/vsftpd.conf.bak"
    fi
    
    # Criar usuário FTP com senha fixa
    echo -e "${NEGRITO}Criando usuário FTP dedicado...${RESET}"
    if id "$USUARIO_FTP" &>/dev/null; then
        echo "Usuário $USUARIO_FTP já existe. Atualizando senha..."
        echo "$USUARIO_FTP:Rai2804@2804" | chpasswd
    else
        useradd -m -s /bin/bash $USUARIO_FTP
        echo "$USUARIO_FTP:Rai2804@2804" | chpasswd
        echo "Usuário $USUARIO_FTP criado com senha fixa: Rai2804@2804"
    fi
    
    # Criar diretório para upload
    mkdir -p $DIRETORIO_FTP
    chown -R $USUARIO_FTP:$USUARIO_FTP $DIRETORIO_FTP
    chmod 755 $DIRETORIO_FTP
    
    # Obter IP da interface principal (mais confiável que IP público)
    IP_LOCAL=$(ip route get 1 | awk '{print $7}' | head -1)
    
    # Configurar VSFTPD com opções mais robustas
    cat > /etc/vsftpd.conf << EOF
# Configuração básica
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd

# Configurações de segurança
session_support=YES
allow_writeable_chroot=YES
hide_ids=YES

# Configurações de conexão
pasv_enable=YES
pasv_min_port=21000
pasv_max_port=21010
# Comente a linha abaixo se estiver atrás de NAT
# pasv_address=$IP_LOCAL
pasv_addr_resolve=NO
port_enable=YES

# Timeouts (em segundos)
idle_session_timeout=600
data_connection_timeout=300
accept_timeout=60
connect_timeout=60

# Limites
max_clients=50
max_per_ip=10
local_root=$DIRETORIO_FTP
EOF

    # Configurar firewall
    echo -e "${NEGRITO}Configurando firewall...${RESET}"
    if command -v ufw &>/dev/null && ufw status | grep -q "active"; then
        ufw allow 21/tcp
        ufw allow 21000:21010/tcp
        echo "Regras de firewall adicionadas para FTP"
    fi

    # Reiniciar o serviço
    systemctl restart vsftpd
    systemctl enable vsftpd
    
    # Verificar status
    if systemctl is-active --quiet vsftpd; then
        echo -e "${VERDE}Servidor FTP configurado com sucesso!${RESET}"
        
        echo
        echo -e "${NEGRITO}==================== INSTRUÇÕES FTP =======================${RESET}"
        echo -e "Dados de conexão:"
        echo -e "  Endereço: ${VERDE}$IP_LOCAL${RESET} (use IP público se estiver acessando externamente)"
        echo -e "  Porta: ${VERDE}21${RESET}"
        echo -e "  Usuário: ${VERDE}$USUARIO_FTP${RESET}"
        echo -e "  Senha: ${VERDE}Rai2804@2804${RESET}"
        echo -e "  Modo: ${VERDE}Passivo (PASV)${RESET}"
        echo -e "  Portas PASV: ${VERDE}21000-21010${RESET}"
        echo
        echo -e "${AMARELO}Importante:${RESET}"
        echo -e "1. Se estiver atrás de um roteador/NAT:"
        echo -e "   - Encaminhe as portas 21 e 21000-21010 para este servidor"
        echo -e "   - Configure o IP externo no cliente FTP"
        echo -e "2. No cliente FTP, habilite o modo PASSIVO"
        echo -e "${NEGRITO}=============================================================${RESET}"
    else
        echo -e "${VERMELHO}Falha ao iniciar o servidor FTP.${RESET}"
        echo -e "Verifique os logs com: ${VERDE}sudo journalctl -u vsftpd.service${RESET}"
        echo -e "Ou visualize em tempo real com: ${VERDE}sudo tail -f /var/log/vsftpd.log${RESET}"
    fi
    
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Instalar dependências
instalar_dependencias() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Instalando dependências do sistema...${RESET}"
    echo
    
    echo "Esta etapa irá instalar todas as dependências necessárias para executar o RuralSys."
    read -p "Deseja continuar? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Instalação de dependências abortada."
        return
    fi
    
    echo
    echo -e "${NEGRITO}Atualizando repositórios...${RESET}"
    apt-get update
    
    echo -e "${NEGRITO}Instalando dependências essenciais...${RESET}"
    apt-get install -y python3 python3-pip python3-venv python3-dev \
                       build-essential libssl-dev libffi-dev \
                       supervisor nginx git curl wget unzip
    
    echo -e "${NEGRITO}Instalando pacotes Python adicionais...${RESET}"
    pip3 install --upgrade pip
    pip3 install gunicorn python-dotenv
    
    echo -e "${VERDE}Dependências instaladas com sucesso!${RESET}"
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Instalar e configurar PostgreSQL
instalar_postgresql() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Instalando e configurando PostgreSQL...${RESET}"
    echo
    
    echo "Esta etapa irá instalar o PostgreSQL e criar um banco de dados para o RuralSys."
    read -p "Deseja continuar? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Instalação do PostgreSQL abortada."
        return
    fi
    
    # Verificar se o PostgreSQL já está instalado
    if command -v psql &>/dev/null; then
        echo -e "${AMARELO}PostgreSQL já está instalado no sistema.${RESET}"
        read -p "Deseja reinstalar? (s/n): " REINSTALAR
        if [[ ! "$REINSTALAR" =~ ^[Ss]$ ]]; then
            echo "Pulando reinstalação do PostgreSQL."
        else
            apt-get purge -y postgresql*
            apt-get autoremove -y
            apt-get update
            echo "PostgreSQL removido. Prosseguindo com a reinstalação."
        fi
    fi
    
    echo -e "${NEGRITO}Instalando PostgreSQL...${RESET}"
    apt-get update
    apt-get install -y postgresql postgresql-contrib
    
    # Iniciar e habilitar o serviço
    systemctl start postgresql
    systemctl enable postgresql
    
    # Verificar status
    if systemctl is-active --quiet postgresql; then
        echo -e "${VERDE}PostgreSQL instalado e em execução!${RESET}"
        
        # Criar banco de dados e usuário
        echo -e "${NEGRITO}Configurando banco de dados...${RESET}"
        
        # Gerar senha aleatória para o banco de dados
        DB_NOME="ruralsys"
        DB_USUARIO="ruralsys_user"
        DB_SENHA="$(openssl rand -base64 12)"
        
        # Criar usuário e banco de dados
        su - postgres -c "psql -c \"CREATE USER $DB_USUARIO WITH PASSWORD '$DB_SENHA';\""
        su - postgres -c "psql -c \"CREATE DATABASE $DB_NOME OWNER $DB_USUARIO;\""
        su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NOME TO $DB_USUARIO;\""
        
        echo -e "${VERDE}Banco de dados configurado com sucesso!${RESET}"
        echo
        echo -e "${NEGRITO}==================== DADOS DO BANCO =======================${RESET}"
        echo -e "  Nome do banco: ${VERDE}$DB_NOME${RESET}"
        echo -e "  Usuário: ${VERDE}$DB_USUARIO${RESET}"
        echo -e "  Senha: ${VERDE}$DB_SENHA${RESET}"
        echo -e "  Host: ${VERDE}localhost${RESET}"
        echo -e "  Porta: ${VERDE}5432${RESET}"
        echo -e "${NEGRITO}=============================================================${RESET}"
        echo
        echo -e "${AMARELO}Anote estas informações! Você precisará delas para configurar o RuralSys.${RESET}"
        
        # Salvar configurações para uso posterior
        mkdir -p $DIRETORIO_TEMP
        cat > $DIRETORIO_TEMP/db_config.env << EOF
DATABASE_URL=postgresql://$DB_USUARIO:$DB_SENHA@localhost:5432/$DB_NOME
PGDATABASE=$DB_NOME
PGUSER=$DB_USUARIO
PGPASSWORD=$DB_SENHA
PGHOST=localhost
PGPORT=5432
EOF
        
        echo "Configurações do banco salvas em $DIRETORIO_TEMP/db_config.env"
    else
        echo -e "${VERMELHO}Falha ao iniciar o PostgreSQL. Verifique os logs:${RESET}"
        echo -e "sudo journalctl -u postgresql.service"
    fi
    
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

extrair_instalar() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Extraindo e instalando o RuralSys...${RESET}"
    echo
    
    # Verificar múltiplos locais possíveis para o arquivo ZIP
    ARQUIVO_ENCONTRADO=""
    LOCAIS_POSSIVEIS=(
        "$DIRETORIO_FTP/$ARQUIVO_ZIP"
        "/tmp/$ARQUIVO_ZIP"
        "/home/$USUARIO/$ARQUIVO_ZIP"
        "$DIRETORIO_INSTALACAO/$ARQUIVO_ZIP"
    )
    
    for local in "${LOCAIS_POSSIVEIS[@]}"; do
        if [ -f "$local" ]; then
            ARQUIVO_ENCONTRADO="$local"
            break
        fi
    done
    
    if [ -z "$ARQUIVO_ENCONTRADO" ]; then
        echo -e "${VERMELHO}Arquivo $ARQUIVO_ZIP não encontrado nos locais esperados.${RESET}"
        echo -e "Por favor, faça upload do arquivo para um destes locais:"
        echo -e "1. Via FTP para: ${VERDE}$DIRETORIO_FTP/${RESET}"
        echo -e "2. Diretamente no servidor em: ${VERDE}/tmp/${RESET}"
        echo -e "3. Ou no seu diretório home: ${VERDE}/home/$USUARIO/${RESET}"
        echo
        echo -e "Você pode usar estes comandos para copiar o arquivo:"
        echo -e "${AZUL}scp ruralsys.zip $USUARIO@$(hostname -I | awk '{print $1}'):/tmp/${RESET}"
        echo -e "${AZUL}ou${RESET}"
        echo -e "${AZUL}lftp -e 'put ruralsys.zip -o $DIRETORIO_FTP/ruralsys.zip; quit' ftp://$USUARIO_FTP:Rai2804@2804@$(hostname -I | awk '{print $1}')${RESET}"
        echo
        read -p "Pressione ENTER após fazer upload do arquivo ou para retornar ao menu principal..."
        return
    fi
    
    echo "Arquivo encontrado em: ${VERDE}$ARQUIVO_ENCONTRADO${RESET}"
    read -p "Deseja continuar com a instalação? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Instalação do RuralSys abortada."
        return
    fi
    
    # Criar diretórios temporários e de instalação
    mkdir -p $DIRETORIO_INSTALACAO $DIRETORIO_TEMP
    
    # Copiar arquivo para o diretório temporário
    echo -e "${NEGRITO}Copiando e extraindo arquivos...${RESET}"
    cp "$ARQUIVO_ENCONTRADO" $DIRETORIO_TEMP/
    
    # Verificar integridade do arquivo ZIP
    if ! unzip -t $DIRETORIO_TEMP/$ARQUIVO_ZIP &>/dev/null; then
        echo -e "${VERMELHO}Erro: O arquivo ZIP está corrompido ou inválido.${RESET}"
        echo -e "Por favor, faça upload novamente do arquivo."
        rm -f $DIRETORIO_TEMP/$ARQUIVO_ZIP
        read -p "Pressione ENTER para retornar ao menu principal..."
        return
    fi
    
    # Extrair arquivos
    unzip -o $DIRETORIO_TEMP/$ARQUIVO_ZIP -d $DIRETORIO_TEMP/
    
    # Verificar se a extração foi bem-sucedida
    if [ ! -d "$DIRETORIO_TEMP/ruralsys" ]; then
        echo -e "${VERMELHO}Erro: Estrutura de diretórios esperada não encontrada no ZIP.${RESET}"
        echo -e "Verifique se o arquivo ZIP contém a pasta 'ruralsys' na raiz."
        read -p "Pressione ENTER para retornar ao menu principal..."
        return
    fi
    
    # Mover para o diretório de instalação
    echo -e "${NEGRITO}Instalando no diretório destino...${RESET}"
    cp -R $DIRETORIO_TEMP/ruralsys/* $DIRETORIO_INSTALACAO/
    
    # Configurar ambiente virtual Python
    echo -e "${NEGRITO}Configurando ambiente virtual Python...${RESET}"
    cd $DIRETORIO_INSTALACAO
    python3 -m venv venv
    source venv/bin/activate
    
    # Instalar dependências Python
    echo -e "${NEGRITO}Instalando dependências Python...${RESET}"
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo -e "${AMARELO}AVISO: arquivo requirements.txt não encontrado.${RESET}"
        echo "Instalando dependências padrão..."
        pip install flask flask-login flask-sqlalchemy flask-wtf gunicorn psycopg2-binary pykml lxml pandas requests sqlalchemy
    fi
    
    # Configurar permissões
    echo -e "${NEGRITO}Configurando permissões...${RESET}"
    chown -R www-data:www-data $DIRETORIO_INSTALACAO
    chmod -R 755 $DIRETORIO_INSTALACAO
    
    echo -e "${VERDE}RuralSys instalado com sucesso em $DIRETORIO_INSTALACAO!${RESET}"
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}
# Configurar serviço systemd
configurar_servico() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Configurando serviço systemd para o RuralSys...${RESET}"
    echo
    
    echo "Esta etapa irá configurar o RuralSys como um serviço do sistema para iniciar automaticamente."
    read -p "Deseja continuar? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Configuração do serviço abortada."
        return
    fi
    
    # Criar arquivo de serviço
    echo -e "${NEGRITO}Criando arquivo de serviço...${RESET}"
    cat > /etc/systemd/system/ruralsys.service << EOF
[Unit]
Description=RuralSys - Sistema de Gestão Rural
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$DIRETORIO_INSTALACAO
ExecStart=$DIRETORIO_INSTALACAO/venv/bin/gunicorn --bind 0.0.0.0:$PORTA_APLICACAO --workers 3 main:app
Restart=always
RestartSec=10
Environment="PATH=$DIRETORIO_INSTALACAO/venv/bin"
EnvironmentFile=$DIRETORIO_INSTALACAO/.env

[Install]
WantedBy=multi-user.target
EOF
    
    # Recarregar configuração do systemd
    systemctl daemon-reload
    
    # Habilitar e iniciar o serviço
    systemctl enable ruralsys.service
    systemctl start ruralsys.service
    
    # Verificar status
    if systemctl is-active --quiet ruralsys.service; then
        echo -e "${VERDE}Serviço RuralSys configurado e iniciado com sucesso!${RESET}"
        
        # Configuração do Nginx como proxy reverso
        echo -e "${NEGRITO}Configurando Nginx como proxy reverso...${RESET}"
        
        if ! command -v nginx &>/dev/null; then
            apt-get update
            apt-get install -y nginx
        fi
        
        # Criar configuração do site
        cat > /etc/nginx/sites-available/ruralsys << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:$PORTA_APLICACAO;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
    
    location /static {
        alias $DIRETORIO_INSTALACAO/static;
    }
}
EOF
        
        # Ativar o site
        ln -sf /etc/nginx/sites-available/ruralsys /etc/nginx/sites-enabled/
        
        # Remover o site padrão
        rm -f /etc/nginx/sites-enabled/default
        
        # Reiniciar o Nginx
        systemctl restart nginx
        systemctl enable nginx
        
        # Obter o IP da máquina
        IP_ADDR=$(hostname -I | awk '{print $1}')
        
        echo -e "${VERDE}Proxy reverso Nginx configurado!${RESET}"
        echo
        echo -e "${NEGRITO}==================== ACESSO AO SISTEMA =======================${RESET}"
        echo -e "O RuralSys está em execução e pode ser acessado em:"
        echo -e "  URL: ${VERDE}http://$IP_ADDR/${RESET}"
        echo -e "  Porta: ${VERDE}80${RESET} (via Nginx)"
        echo -e "  Usuário padrão: ${VERDE}admin@fazenda.com${RESET}"
        echo -e "  Senha padrão: ${VERDE}admin${RESET}"
        echo -e "${NEGRITO}===============================================================${RESET}"
    else
        echo -e "${VERMELHO}Falha ao iniciar o serviço RuralSys. Verifique os logs:${RESET}"
        echo -e "sudo journalctl -u ruralsys.service"
    fi
    
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Configurar portas da aplicação
configurar_portas() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Configurando portas da aplicação RuralSys...${RESET}"
    echo
    
    echo "Esta etapa permite configurar as portas que o RuralSys utilizará."
    echo "Isso é útil quando você tem várias aplicações no mesmo servidor."
    echo
    echo -e "${NEGRITO}Configurações atuais:${RESET}"
    echo -e "  Porta da aplicação Flask/Gunicorn: ${VERDE}$PORTA_APLICACAO${RESET}"
    echo -e "  Porta HTTP do Nginx: ${VERDE}$PORTA_HTTP${RESET}"
    echo
    
    read -p "Deseja alterar estas configurações? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Configuração de portas abortada."
        return
    fi
    
    # Configurar porta da aplicação
    echo
    echo -e "${NEGRITO}Configuração da porta da aplicação Flask/Gunicorn:${RESET}"
    echo "Esta é a porta interna que o servidor Gunicorn utilizará."
    echo "Recomendado: utilize portas entre 5000-9000 que não estejam em uso."
    echo "Porta atual: $PORTA_APLICACAO"
    read -p "Nova porta (pressione ENTER para manter a atual): " NOVA_PORTA
    
    if [[ -n "$NOVA_PORTA" ]]; then
        # Validar se a porta é um número e está em um intervalo válido
        if [[ "$NOVA_PORTA" =~ ^[0-9]+$ ]] && [ "$NOVA_PORTA" -ge 1024 ] && [ "$NOVA_PORTA" -le 65535 ]; then
            PORTA_APLICACAO=$NOVA_PORTA
            echo -e "Porta da aplicação alterada para: ${VERDE}$PORTA_APLICACAO${RESET}"
            
            # Verificar se a porta está em uso
            if netstat -tuln | grep -q ":$PORTA_APLICACAO "; then
                echo -e "${AMARELO}AVISO: A porta $PORTA_APLICACAO parece estar em uso por outro serviço.${RESET}"
                echo -e "Você pode verificar com: sudo netstat -tuln | grep '$PORTA_APLICACAO'"
                read -p "Deseja continuar mesmo assim? (s/n): " CONTINUAR
                if [[ ! "$CONTINUAR" =~ ^[Ss]$ ]]; then
                    echo "Configuração de portas abortada."
                    return
                fi
            fi
        else
            echo -e "${VERMELHO}Porta inválida. Mantendo a porta atual: $PORTA_APLICACAO${RESET}"
        fi
    else
        echo -e "Mantendo a porta atual: ${VERDE}$PORTA_APLICACAO${RESET}"
    fi
    
    # Configurar porta HTTP
    echo
    echo -e "${NEGRITO}Configuração da porta HTTP (Nginx):${RESET}"
    echo "Esta é a porta externa que os usuários utilizarão para acessar o sistema."
    echo "Padrão: 80 (HTTP padrão)"
    echo "Porta atual: $PORTA_HTTP"
    read -p "Nova porta (pressione ENTER para manter a atual): " NOVA_PORTA_HTTP
    
    if [[ -n "$NOVA_PORTA_HTTP" ]]; then
        # Validar se a porta é um número e está em um intervalo válido
        if [[ "$NOVA_PORTA_HTTP" =~ ^[0-9]+$ ]] && [ "$NOVA_PORTA_HTTP" -ge 1 ] && [ "$NOVA_PORTA_HTTP" -le 65535 ]; then
            PORTA_HTTP=$NOVA_PORTA_HTTP
            echo -e "Porta HTTP alterada para: ${VERDE}$PORTA_HTTP${RESET}"
            
            # Verificar se a porta está em uso
            if netstat -tuln | grep -q ":$PORTA_HTTP "; then
                echo -e "${AMARELO}AVISO: A porta $PORTA_HTTP parece estar em uso por outro serviço.${RESET}"
                echo -e "Você pode verificar com: sudo netstat -tuln | grep '$PORTA_HTTP'"
                read -p "Deseja continuar mesmo assim? (s/n): " CONTINUAR
                if [[ ! "$CONTINUAR" =~ ^[Ss]$ ]]; then
                    echo "Configuração de portas abortada."
                    return
                fi
            fi
        else
            echo -e "${VERMELHO}Porta inválida. Mantendo a porta atual: $PORTA_HTTP${RESET}"
        fi
    else
        echo -e "Mantendo a porta atual: ${VERDE}$PORTA_HTTP${RESET}"
    fi
    
    # Salvar configurações
    echo
    echo -e "${NEGRITO}Salvando configurações...${RESET}"
    mkdir -p $DIRETORIO_TEMP
    echo "PORTA_APLICACAO=$PORTA_APLICACAO" > $DIRETORIO_TEMP/portas.conf
    echo "PORTA_HTTP=$PORTA_HTTP" >> $DIRETORIO_TEMP/portas.conf
    
    # Atualizar serviço se já estiver configurado
    if [ -f /etc/systemd/system/ruralsys.service ]; then
        echo -e "${NEGRITO}Atualizando configuração do serviço...${RESET}"
        
        # Atualizar arquivo de serviço
        sed -i "s/--bind 0.0.0.0:[0-9]\+/--bind 0.0.0.0:$PORTA_APLICACAO/g" /etc/systemd/system/ruralsys.service
        
        # Recarregar configuração
        systemctl daemon-reload
        
        # Reiniciar serviço se estiver ativo
        if systemctl is-active --quiet ruralsys.service; then
            echo -e "Reiniciando serviço RuralSys..."
            systemctl restart ruralsys.service
        fi
    fi
    
    # Atualizar Nginx se já estiver configurado
    if [ -f /etc/nginx/sites-available/ruralsys ]; then
        echo -e "${NEGRITO}Atualizando configuração do Nginx...${RESET}"
        
        # Atualizar porta de escuta
        sed -i "s/listen [0-9]\+;/listen $PORTA_HTTP;/g" /etc/nginx/sites-available/ruralsys
        
        # Atualizar proxy_pass
        sed -i "s/proxy_pass http:\/\/127.0.0.1:[0-9]\+;/proxy_pass http:\/\/127.0.0.1:$PORTA_APLICACAO;/g" /etc/nginx/sites-available/ruralsys
        
        # Reiniciar Nginx
        systemctl restart nginx
    fi
    
    echo
    echo -e "${VERDE}Configurações de porta atualizadas com sucesso!${RESET}"
    echo -e "${NEGRITO}==================== NOVAS CONFIGURAÇÕES =======================${RESET}"
    echo -e "  Porta da aplicação: ${VERDE}$PORTA_APLICACAO${RESET}"
    echo -e "  Porta HTTP: ${VERDE}$PORTA_HTTP${RESET}"
    echo -e "${NEGRITO}===============================================================${RESET}"
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Testar a instalação
testar_instalacao() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Testando a instalação do RuralSys...${RESET}"
    echo
    
    # Verificar se o serviço está em execução
    echo -e "${NEGRITO}Verificando status do serviço...${RESET}"
    if systemctl is-active --quiet ruralsys.service; then
        echo -e "Status do serviço: ${VERDE}Ativo${RESET}"
    else
        echo -e "Status do serviço: ${VERMELHO}Inativo${RESET}"
        echo -e "Tentando iniciar o serviço..."
        systemctl start ruralsys.service
        sleep 2
        
        if systemctl is-active --quiet ruralsys.service; then
            echo -e "Status do serviço após reinício: ${VERDE}Ativo${RESET}"
        else
            echo -e "Status do serviço após reinício: ${VERMELHO}Inativo${RESET}"
            echo -e "Verifique os logs: sudo journalctl -u ruralsys.service"
        fi
    fi
    
    # Verificar conexão com o banco de dados
    echo -e "${NEGRITO}Verificando conexão com o banco de dados...${RESET}"
    if [ -f "$DIRETORIO_INSTALACAO/.env" ]; then
        source $DIRETORIO_INSTALACAO/.env
        
        if su - postgres -c "psql -lqt | cut -d \| -f 1 | grep -qw $PGDATABASE"; then
            echo -e "Banco de dados: ${VERDE}Conectado${RESET}"
        else
            echo -e "Banco de dados: ${VERMELHO}Não encontrado${RESET}"
        fi
    else
        echo -e "Arquivo .env não encontrado. Não foi possível verificar a conexão com o banco de dados."
    fi
    
    # Verificar se o Nginx está servindo a aplicação
    echo -e "${NEGRITO}Verificando configuração do Nginx...${RESET}"
    if systemctl is-active --quiet nginx; then
        echo -e "Status do Nginx: ${VERDE}Ativo${RESET}"
        
        # Verificar configuração
        if [ -f /etc/nginx/sites-enabled/ruralsys ]; then
            echo -e "Configuração do site: ${VERDE}OK${RESET}"
        else
            echo -e "Configuração do site: ${VERMELHO}Não encontrada${RESET}"
        fi
    else
        echo -e "Status do Nginx: ${VERMELHO}Inativo${RESET}"
        echo -e "Tentando iniciar o Nginx..."
        systemctl start nginx
    fi
    
    # Testar acesso à aplicação
    echo -e "${NEGRITO}Testando acesso à aplicação...${RESET}"
    IP_ADDR=$(hostname -I | awk '{print $1}')
    
    if command -v curl &>/dev/null; then
        RESPOSTA=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORTA_APLICACAO/)
        
        if [ "$RESPOSTA" == "200" ] || [ "$RESPOSTA" == "302" ]; then
            echo -e "Acesso à aplicação: ${VERDE}OK (HTTP $RESPOSTA)${RESET}"
        else
            echo -e "Acesso à aplicação: ${VERMELHO}Falha (HTTP $RESPOSTA)${RESET}"
        fi
    else
        echo -e "${AMARELO}curl não encontrado. Não foi possível testar o acesso via HTTP.${RESET}"
    fi
    
    echo
    echo -e "${NEGRITO}==================== RESULTADO DO TESTE =======================${RESET}"
    echo -e "Acesse o RuralSys em: ${VERDE}http://$IP_ADDR/${RESET}"
    echo -e "${NEGRITO}===============================================================${RESET}"
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Realizar instalação automática
instalacao_automatica() {
    imprimir_cabecalho
    echo -e "${NEGRITO}Iniciando instalação automática do RuralSys...${RESET}"
    echo
    
    echo "Esta opção irá executar todas as etapas de instalação automaticamente."
    echo -e "${AMARELO}ATENÇÃO: É necessário ter o arquivo $ARQUIVO_ZIP disponível para upload via FTP.${RESET}"
    read -p "Deseja continuar? (s/n): " RESPOSTA
    if [[ ! "$RESPOSTA" =~ ^[Ss]$ ]]; then
        echo "Instalação automática abortada."
        return
    fi
    
    # Executar todas as etapas
    echo
    echo -e "${NEGRITO}Etapa 1/7: Verificando requisitos...${RESET}"
    verificar_requisitos
    
    echo
    echo -e "${NEGRITO}Etapa 2/7: Configurando servidor FTP...${RESET}"
    configurar_ftp
    
    echo
    echo -e "${AMARELO}PAUSA: Agora faça upload do arquivo $ARQUIVO_ZIP via FTP.${RESET}"
    echo -e "Use um cliente FTP (como FileZilla) para fazer upload para:"
    echo -e "  Servidor: $(hostname -I | awk '{print $1}')"
    echo -e "  Usuário: $USUARIO_FTP"
    echo -e "  Senha: $SENHA_FTP"
    echo -e "  Diretório: $DIRETORIO_FTP"
    echo
    read -p "Após concluir o upload, pressione ENTER para continuar..."
    
    echo
    echo -e "${NEGRITO}Etapa 3/7: Configurando portas da aplicação...${RESET}"
    
    # Configuração simplificada de portas para o modo automático
    echo -e "O RuralSys será instalado com as seguintes portas padrão:"
    echo -e "  Porta da aplicação Flask/Gunicorn: ${VERDE}$PORTA_APLICACAO${RESET}"
    echo -e "  Porta HTTP do Nginx: ${VERDE}$PORTA_HTTP${RESET}"
    echo
    read -p "Deseja personalizar estas portas? (s/n): " PERSONALIZAR_PORTAS
    if [[ "$PERSONALIZAR_PORTAS" =~ ^[Ss]$ ]]; then
        configurar_portas
    fi
    
    echo
    echo -e "${NEGRITO}Etapa 4/7: Instalando dependências...${RESET}"
    instalar_dependencias
    
    echo
    echo -e "${NEGRITO}Etapa 5/7: Instalando PostgreSQL...${RESET}"
    instalar_postgresql
    
    echo
    echo -e "${NEGRITO}Etapa 6/7: Extraindo e instalando RuralSys...${RESET}"
    extrair_instalar
    
    echo
    echo -e "${NEGRITO}Etapa 7/7: Configurando serviço...${RESET}"
    configurar_servico
    
    echo
    echo -e "${NEGRITO}Testando a instalação...${RESET}"
    testar_instalacao
    
    echo
    echo -e "${VERDE}${NEGRITO}==================== INSTALAÇÃO CONCLUÍDA =======================${RESET}"
    echo -e "${VERDE}O RuralSys foi instalado com sucesso!${RESET}"
    echo -e "Acesse o sistema em: ${VERDE}http://$(hostname -I | awk '{print $1}')/${RESET}"
    echo -e "Usuário padrão: ${VERDE}admin@fazenda.com${RESET}"
    echo -e "Senha padrão: ${VERDE}admin${RESET}"
    echo -e "${VERDE}${NEGRITO}===============================================================${RESET}"
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Desinstalar RuralSys
desinstalar_ruralsys() {
    imprimir_cabecalho
    echo -e "${VERMELHO}${NEGRITO}Desinstalando RuralSys...${RESET}"
    echo
    
    echo -e "${VERMELHO}ATENÇÃO: Esta ação removerá completamente o RuralSys e todos os seus dados.${RESET}"
    echo -e "${VERMELHO}Esta ação é IRREVERSÍVEL!${RESET}"
    echo
    
    read -p "Digite 'DESINSTALAR' para confirmar a desinstalação: " CONFIRMAR
    if [ "$CONFIRMAR" != "DESINSTALAR" ]; then
        echo "Desinstalação abortada."
        return
    fi
    
    echo
    echo -e "${NEGRITO}Parando serviços...${RESET}"
    systemctl stop ruralsys.service 2>/dev/null
    systemctl disable ruralsys.service 2>/dev/null
    
    echo -e "${NEGRITO}Removendo arquivos de serviço...${RESET}"
    rm -f /etc/systemd/system/ruralsys.service
    systemctl daemon-reload
    
    echo -e "${NEGRITO}Removendo configuração do Nginx...${RESET}"
    rm -f /etc/nginx/sites-enabled/ruralsys
    rm -f /etc/nginx/sites-available/ruralsys
    systemctl restart nginx
    
    echo -e "${NEGRITO}Removendo arquivos de instalação...${RESET}"
    rm -rf $DIRETORIO_INSTALACAO
    rm -rf $DIRETORIO_TEMP
    
    echo -e "${NEGRITO}Desinstalando servidor FTP...${RESET}"
    read -p "Deseja remover o servidor FTP também? (s/n): " REMOVER_FTP
    if [[ "$REMOVER_FTP" =~ ^[Ss]$ ]]; then
        systemctl stop vsftpd 2>/dev/null
        systemctl disable vsftpd 2>/dev/null
        apt-get purge -y vsftpd
        
        read -p "Remover usuário FTP e seus arquivos? (s/n): " REMOVER_USUARIO
        if [[ "$REMOVER_USUARIO" =~ ^[Ss]$ ]]; then
            userdel -r $USUARIO_FTP 2>/dev/null
            rm -rf $DIRETORIO_FTP
        fi
    fi
    
    echo -e "${NEGRITO}Removendo banco de dados...${RESET}"
    read -p "Deseja remover o banco de dados PostgreSQL? (s/n): " REMOVER_DB
    if [[ "$REMOVER_DB" =~ ^[Ss]$ ]]; then
        if [ -f "$DIRETORIO_TEMP/db_config.env" ]; then
            source $DIRETORIO_TEMP/db_config.env
            su - postgres -c "psql -c 'DROP DATABASE IF EXISTS $PGDATABASE;'"
            su - postgres -c "psql -c 'DROP USER IF EXISTS $PGUSER;'"
        else
            read -p "Nome do banco de dados a remover: " DB_NOME
            read -p "Nome do usuário do banco a remover: " DB_USUARIO
            
            su - postgres -c "psql -c 'DROP DATABASE IF EXISTS $DB_NOME;'"
            su - postgres -c "psql -c 'DROP USER IF EXISTS $DB_USUARIO;'"
        fi
        
        read -p "Desinstalar PostgreSQL? (s/n): " DESINSTALAR_PG
        if [[ "$DESINSTALAR_PG" =~ ^[Ss]$ ]]; then
            apt-get purge -y postgresql*
            apt-get autoremove -y
        fi
    fi
    
    echo
    echo -e "${VERDE}RuralSys foi desinstalado com sucesso!${RESET}"
    echo
    read -p "Pressione ENTER para retornar ao menu principal..."
}

# Função principal
main() {
    verificar_root
    
    while true; do
        imprimir_menu
        read -p "Opção: " OPCAO
        
        case $OPCAO in
            1) verificar_requisitos ;;
            2) configurar_ftp ;;
            3) instalar_dependencias ;;
            4) instalar_postgresql ;;
            5) extrair_instalar ;;
            6) configurar_servico ;;
            7) configurar_portas ;;
            8) testar_instalacao ;;
            9) instalacao_automatica ;;
            10) desinstalar_ruralsys ;;
            0) 
                echo -e "${VERDE}Obrigado por usar o instalador do RuralSys!${RESET}"
                exit 0
                ;;
            *)
                echo -e "${VERMELHO}Opção inválida. Por favor, tente novamente.${RESET}"
                sleep 2
                ;;
        esac
    done
}

# Iniciar o script
main