#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador Automático do Sistema de Gestão Agropecuária
Desenvolvido para facilitar a instalação através do CyberPanel
"""

import os
import sys
import json
import subprocess
import shutil
import getpass
import platform
import random
import string
import time
from datetime import datetime

# Cores para saída no terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Banner do instalador
def show_banner():
    banner = f"""
{Colors.GREEN}
  _____  _    _ _____            _      _______     _______ 
 |  __ \\| |  | |  __ \\     /\\   | |    / ____\\ \\   / / ____|
 | |__) | |  | | |__) |   /  \\  | |   | (___  \\ \\_/ / (___  
 |  _  /| |  | |  _  /   / /\\ \\ | |    \\___ \\  \\   / \\___ \\ 
 | | \\ \\| |__| | | \\ \\  / ____ \\| |________) |  | |  ____) |
 |_|  \\_\\\\____/|_|  \\_\\/_/    \\_\\______|_____/   |_| |_____/ 
                                                           
{Colors.BLUE}=== INSTALADOR AUTOMÁTICO - SISTEMA DE GESTÃO AGROPECUÁRIA ==={Colors.ENDC}
{Colors.BOLD}Versão 1.0 - RuralSys Inovação Tecnológica{Colors.ENDC}
"""
    print(banner)

# Funções de utilitário
def random_string(length=16):
    """Gera uma string aleatória para uso como chave secreta"""
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

def run_command(command, show_output=True):
    """Executa um comando de shell e retorna o resultado"""
    try:
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if show_output and stdout:
            print(stdout)
        if stderr:
            print(f"{Colors.FAIL}ERRO: {stderr}{Colors.ENDC}")
            
        return process.returncode, stdout, stderr
    except Exception as e:
        print(f"{Colors.FAIL}Erro ao executar comando: {str(e)}{Colors.ENDC}")
        return 1, "", str(e)

def detect_environment():
    """Detecta o ambiente de execução"""
    system = platform.system()
    
    # Verifica CyberPanel
    is_cyberpanel = os.path.exists('/usr/local/CyberCP')
    
    # Verifica se está na pasta public_html
    cwd = os.getcwd()
    is_public_html = 'public_html' in cwd
    
    # Verifica acesso ao Python
    python_version = platform.python_version()
    
    # Verifica acesso ao PostgreSQL
    has_postgres = run_command("which psql", show_output=False)[0] == 0
    
    return {
        "system": system,
        "is_cyberpanel": is_cyberpanel,
        "is_public_html": is_public_html,
        "python_version": python_version,
        "has_postgres": has_postgres,
        "current_path": cwd
    }

def create_python_venv():
    """Cria e ativa um ambiente virtual Python"""
    print(f"{Colors.BLUE}Criando ambiente virtual Python...{Colors.ENDC}")
    
    if os.path.exists("venv"):
        print(f"{Colors.WARNING}Ambiente virtual já existe. Usando o existente.{Colors.ENDC}")
        return True
    
    status, _, _ = run_command("python3 -m venv venv")
    if status != 0:
        print(f"{Colors.FAIL}Falha ao criar ambiente virtual.{Colors.ENDC}")
        return False
        
    print(f"{Colors.GREEN}Ambiente virtual criado com sucesso.{Colors.ENDC}")
    return True

def install_requirements():
    """Instala os pacotes necessários"""
    print(f"{Colors.BLUE}Instalando dependências...{Colors.ENDC}")
    
    # Ativa o ambiente virtual antes de instalar
    if os.name == 'nt':  # Windows
        venv_python = os.path.join("venv", "Scripts", "python")
        venv_pip = os.path.join("venv", "Scripts", "pip")
    else:  # Unix/Linux
        venv_python = os.path.join("venv", "bin", "python")
        venv_pip = os.path.join("venv", "bin", "pip")
    
    # Lista de pacotes necessários
    packages = [
        "flask",
        "flask-login", 
        "flask-sqlalchemy", 
        "flask-wtf",
        "gunicorn",
        "psycopg2-binary",
        "werkzeug",
        "pandas",
        "xlsxwriter",
        "email-validator"
    ]
    
    for package in packages:
        print(f"Instalando {package}...")
        status, _, _ = run_command(f"{venv_pip} install {package}", show_output=False)
        if status != 0:
            print(f"{Colors.FAIL}Falha ao instalar {package}.{Colors.ENDC}")
            return False
    
    print(f"{Colors.GREEN}Todas as dependências instaladas com sucesso.{Colors.ENDC}")
    return True

def setup_database(db_name, db_user, db_password):
    """Configura o banco de dados PostgreSQL"""
    print(f"{Colors.BLUE}Configurando banco de dados PostgreSQL...{Colors.ENDC}")
    
    # Verifica se o PostgreSQL está instalado
    status, _, _ = run_command("which psql", show_output=False)
    if status != 0:
        print(f"{Colors.FAIL}PostgreSQL não encontrado. Por favor, instale o PostgreSQL.{Colors.ENDC}")
        return False
    
    # Verifica se o usuário já existe
    status, output, _ = run_command(f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='{db_user}'\"", show_output=False)
    user_exists = output.strip() == "1"
    
    if not user_exists:
        print(f"Criando usuário {db_user}...")
        status, _, _ = run_command(f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_password}';\"", show_output=False)
        if status != 0:
            print(f"{Colors.FAIL}Falha ao criar usuário.{Colors.ENDC}")
            return False
    
    # Verifica se o banco de dados já existe
    status, output, _ = run_command(f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='{db_name}'\"", show_output=False)
    db_exists = output.strip() == "1"
    
    if not db_exists:
        print(f"Criando banco de dados {db_name}...")
        status, _, _ = run_command(f"sudo -u postgres psql -c \"CREATE DATABASE {db_name} OWNER {db_user};\"", show_output=False)
        if status != 0:
            print(f"{Colors.FAIL}Falha ao criar banco de dados.{Colors.ENDC}")
            return False
    
    print(f"{Colors.GREEN}Banco de dados configurado com sucesso.{Colors.ENDC}")
    return True

def create_env_file(db_user, db_password, db_name, host="localhost"):
    """Cria o arquivo .env com as configurações necessárias"""
    print(f"{Colors.BLUE}Criando arquivo de configuração .env...{Colors.ENDC}")
    
    # Gera uma chave secreta aleatória
    secret_key = random_string(32)
    
    env_content = f"""DATABASE_URL=postgresql://{db_user}:{db_password}@{host}/{db_name}
SESSION_SECRET={secret_key}
FLASK_APP=main.py
FLASK_ENV=production
"""
    
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        print(f"{Colors.GREEN}Arquivo .env criado com sucesso.{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.FAIL}Erro ao criar arquivo .env: {str(e)}{Colors.ENDC}")
        return False

def initialize_database():
    """Inicializa o banco de dados com as tabelas e dados iniciais"""
    print(f"{Colors.BLUE}Inicializando banco de dados...{Colors.ENDC}")
    
    if os.name == 'nt':  # Windows
        venv_python = os.path.join("venv", "Scripts", "python")
    else:  # Unix/Linux
        venv_python = os.path.join("venv", "bin", "python")
    
    # Executa o script de criação das tabelas
    init_script = """
from app import app
from main import db
app.app_context().push()
db.create_all()
print("Banco de dados inicializado com sucesso!")
"""
    
    try:
        with open("init_db_script.py", "w") as f:
            f.write(init_script)
        
        status, _, _ = run_command(f"{venv_python} init_db_script.py")
        if status != 0:
            print(f"{Colors.FAIL}Falha ao inicializar banco de dados.{Colors.ENDC}")
            return False
        
        # Remove o script temporário
        os.remove("init_db_script.py")
        print(f"{Colors.GREEN}Banco de dados inicializado com sucesso.{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.FAIL}Erro ao inicializar banco de dados: {str(e)}{Colors.ENDC}")
        return False

def setup_cyberpanel_application():
    """Configura a aplicação no CyberPanel"""
    print(f"{Colors.BLUE}Configurando aplicação no CyberPanel...{Colors.ENDC}")
    
    # Detecta o caminho atual e o domínio baseado no caminho
    current_path = os.getcwd()
    parts = current_path.split('/')
    
    try:
        # Tenta encontrar o domínio no caminho
        domain_index = parts.index('public_html') - 1
        domain = parts[domain_index] if domain_index >= 0 else None
        
        if domain:
            print(f"Domínio detectado: {domain}")
            
            # Cria um arquivo de configuração do Gunicorn
            gunicorn_conf = """import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
max_requests = 1000
max_requests_jitter = 50
timeout = 30
"""
            with open("gunicorn_conf.py", "w") as f:
                f.write(gunicorn_conf)
            
            # Cria um arquivo .htaccess para redirecionar através do proxy se necessário
            htaccess = """
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(.*)$ http://localhost:5000/$1 [P,L]
</IfModule>
"""
            try:
                with open(".htaccess", "w") as f:
                    f.write(htaccess)
            except:
                print(f"{Colors.WARNING}Não foi possível criar .htaccess. Você talvez precise configurar proxy manualmente.{Colors.ENDC}")
            
            print(f"{Colors.GREEN}Configuração do CyberPanel concluída.{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.WARNING}Não foi possível detectar o domínio a partir do caminho atual.{Colors.ENDC}")
            return False
    except:
        print(f"{Colors.WARNING}Erro ao configurar aplicação no CyberPanel.{Colors.ENDC}")
        return False

def create_service_file():
    """Cria um arquivo de serviço systemd para execução contínua"""
    print(f"{Colors.BLUE}Criando arquivo de serviço...{Colors.ENDC}")
    
    current_path = os.getcwd()
    service_content = f"""[Unit]
Description=Sistema de Gestão Agropecuária
After=network.target postgresql.service

[Service]
User={getpass.getuser()}
WorkingDirectory={current_path}
ExecStart={current_path}/venv/bin/gunicorn --config gunicorn_conf.py main:app
Restart=always

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open("fazenda.service", "w") as f:
            f.write(service_content)
        
        print(f"{Colors.GREEN}Arquivo de serviço criado: {current_path}/fazenda.service{Colors.ENDC}")
        print(f"Para instalar o serviço, execute como root:")
        print(f"  cp {current_path}/fazenda.service /etc/systemd/system/")
        print(f"  systemctl enable fazenda.service")
        print(f"  systemctl start fazenda.service")
        
        return True
    except Exception as e:
        print(f"{Colors.FAIL}Erro ao criar arquivo de serviço: {str(e)}{Colors.ENDC}")
        return False

def cleanup_installation():
    """Remove arquivos temporários de instalação"""
    print(f"{Colors.BLUE}Limpando arquivos de instalação...{Colors.ENDC}")
    
    # Lista de arquivos temporários para remover
    temp_files = [
        "install.py"  # Removerá a si mesmo
    ]
    
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"Removido: {file}")
        except Exception as e:
            print(f"{Colors.WARNING}Não foi possível remover {file}: {str(e)}{Colors.ENDC}")
    
    print(f"{Colors.GREEN}Limpeza concluída.{Colors.ENDC}")
    return True

def create_installation_log(env_info, success=True):
    """Cria um registro da instalação"""
    log_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": env_info,
        "success": success,
        "version": "1.0"
    }
    
    try:
        with open("instalacao.log", "w") as f:
            json.dump(log_data, f, indent=2)
        
        return True
    except:
        return False

def create_readme_file():
    """Cria um arquivo README com instruções de acesso"""
    readme_content = """# Sistema de Gestão Agropecuária - Instalação Concluída

## Como Acessar o Sistema

1. Se você instalou através do CyberPanel:
   - Acesse pelo seu domínio: https://seu-dominio.com
   - Para inicializar o banco de dados com dados iniciais: https://seu-dominio.com/init_db
   
2. Se você instalou em um servidor dedicado:
   - Certifique-se de que o serviço está em execução: `systemctl status fazenda.service`
   - Acesse pelo endereço: http://seu-ip-ou-dominio:5000
   - Para inicializar o banco de dados com dados iniciais: http://seu-ip-ou-dominio:5000/init_db

## Credenciais Padrão

Após inicializar o banco de dados, você pode fazer login com:
- Email: admin@fazenda.com
- Senha: admin

**Importante:** Altere a senha padrão após o primeiro login!

## Documentação

Consulte a pasta `docs` para obter informações detalhadas sobre:
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
"""
    
    try:
        with open("INSTALACAO.md", "w") as f:
            f.write(readme_content)
        
        return True
    except:
        return False

def main():
    """Função principal do instalador"""
    show_banner()
    
    print(f"{Colors.BLUE}Iniciando instalação do Sistema de Gestão Agropecuária...{Colors.ENDC}")
    print(f"Data e hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Diretório atual: {os.getcwd()}")
    print("")
    
    # Detecta o ambiente
    env_info = detect_environment()
    print(f"{Colors.BOLD}Informações do ambiente:{Colors.ENDC}")
    print(f"Sistema operacional: {env_info['system']}")
    print(f"CyberPanel detectado: {'Sim' if env_info['is_cyberpanel'] else 'Não'}")
    print(f"Pasta public_html: {'Sim' if env_info['is_public_html'] else 'Não'}")
    print(f"Versão do Python: {env_info['python_version']}")
    print(f"PostgreSQL instalado: {'Sim' if env_info['has_postgres'] else 'Não'}")
    print("")
    
    # Configuração do banco de dados
    db_name = "fazenda"
    db_user = "fazenda"
    db_password = random_string(12)
    
    print(f"{Colors.BOLD}Configuração do banco de dados:{Colors.ENDC}")
    print(f"Nome do banco: {db_name}")
    print(f"Usuário: {db_user}")
    print(f"Senha: {db_password}")
    print("")
    
    # Confirmar instalação
    if input(f"{Colors.WARNING}Deseja prosseguir com a instalação? (s/n): {Colors.ENDC}").lower() != 's':
        print("Instalação cancelada pelo usuário.")
        return
    
    # Etapas de instalação
    steps = []
    
    # 1. Criar ambiente virtual
    steps.append(("Ambiente virtual", create_python_venv()))
    
    # 2. Instalar dependências
    steps.append(("Instalação de dependências", install_requirements()))
    
    # 3. Configurar banco de dados (se PostgreSQL estiver instalado)
    if env_info['has_postgres']:
        steps.append(("Configuração do banco de dados", setup_database(db_name, db_user, db_password)))
    
    # 4. Criar arquivo .env
    steps.append(("Criação do arquivo .env", create_env_file(db_user, db_password, db_name)))
    
    # 5. Inicializar banco de dados
    steps.append(("Inicialização do banco de dados", initialize_database()))
    
    # 6. Configuração específica do CyberPanel
    if env_info['is_cyberpanel'] or env_info['is_public_html']:
        steps.append(("Configuração do CyberPanel", setup_cyberpanel_application()))
    
    # 7. Criar arquivo de serviço
    steps.append(("Criação do arquivo de serviço", create_service_file()))
    
    # 8. Criar arquivo README
    steps.append(("Criação do arquivo README", create_readme_file()))
    
    # Resumo da instalação
    print(f"\n{Colors.BOLD}Resumo da instalação:{Colors.ENDC}")
    all_success = True
    
    for step, success in steps:
        status = f"{Colors.GREEN}✓ Sucesso{Colors.ENDC}" if success else f"{Colors.FAIL}✗ Falha{Colors.ENDC}"
        print(f"{step}: {status}")
        if not success:
            all_success = False
    
    # Registro da instalação
    create_installation_log(env_info, all_success)
    
    if all_success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}Instalação concluída com sucesso!{Colors.ENDC}")
        print("\nInstruções de acesso:")
        print("1. Se você instalou através do CyberPanel:")
        print("   - Acesse pelo seu domínio: https://seu-dominio.com")
        print("   - Para inicializar o banco de dados com dados iniciais: https://seu-dominio.com/init_db")
        print("\n2. Se você instalou em um servidor dedicado:")
        print("   - Inicie o serviço: systemctl start fazenda.service")
        print("   - Acesse pelo endereço: http://seu-ip-ou-dominio:5000")
        print("   - Para inicializar o banco de dados com dados iniciais: http://seu-ip-ou-dominio:5000/init_db")
        print("\nCredenciais padrão após inicialização:")
        print("- Email: admin@fazenda.com")
        print("- Senha: admin")
        print("\nIMPORTANTE: Altere a senha padrão após o primeiro login!")
        
        # Limpar arquivos de instalação
        if input(f"\n{Colors.WARNING}Remover arquivos de instalação? (s/n): {Colors.ENDC}").lower() == 's':
            cleanup_installation()
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}A instalação foi concluída, mas com alguns erros.{Colors.ENDC}")
        print("Verifique os erros acima e consulte a documentação para solucioná-los.")
        print("Os registros da instalação foram salvos em instalacao.log para referência.")
    
    print(f"\n{Colors.BLUE}Obrigado por instalar o Sistema de Gestão Agropecuária!{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInstalação interrompida pelo usuário.")
    except Exception as e:
        print(f"\n{Colors.FAIL}Erro inesperado durante a instalação: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()