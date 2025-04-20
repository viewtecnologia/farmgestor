#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para realizar migrações do banco de dados

Este script é utilizado para atualizar o esquema do banco de dados 
quando houver modificações nos modelos de dados.
"""

import os
import sys
import argparse
from datetime import datetime

# Configurar para importar módulos do sistema
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

try:
    from models import db
    from app import app
except ImportError:
    print("Erro ao importar módulos. Verifique se você está no diretório correto.")
    sys.exit(1)

def criar_backup(conn_string=None):
    """
    Cria um backup do banco de dados antes da migração
    
    Args:
        conn_string: String de conexão com o banco de dados
    
    Returns:
        str: Caminho do arquivo de backup ou None se falhar
    """
    try:
        # Se a string de conexão não for fornecida, tenta pegar do app
        if conn_string is None:
            conn_string = app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if not conn_string:
            print("Erro: Não foi possível determinar a string de conexão com o banco de dados.")
            return None
        
        # Extrai informações da string de conexão
        # Formato: postgresql://usuario:senha@host:porta/banco
        if conn_string.startswith('postgresql://'):
            # Remove 'postgresql://'
            conn_info = conn_string[13:]
            
            # Separa usuário:senha@host:porta/banco
            auth_host_db = conn_info.split('@')
            if len(auth_host_db) != 2:
                print("Erro: Formato da string de conexão não reconhecido.")
                return None
            
            auth = auth_host_db[0]
            host_db = auth_host_db[1]
            
            # Separa usuário:senha
            auth_parts = auth.split(':')
            if len(auth_parts) != 2:
                print("Erro: Formato das credenciais não reconhecido.")
                return None
            
            usuario = auth_parts[0]
            senha = auth_parts[1]
            
            # Separa host:porta/banco
            host_port_db = host_db.split('/')
            if len(host_port_db) != 2:
                print("Erro: Formato do host/banco não reconhecido.")
                return None
            
            host_port = host_port_db[0]
            banco = host_port_db[1]
            
            # Separa host:porta (porta é opcional)
            host_parts = host_port.split(':')
            host = host_parts[0]
            porta = host_parts[1] if len(host_parts) > 1 else '5432'
            
            # Cria diretório de backups se não existir
            backup_dir = os.path.join(script_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Nome do arquivo de backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'backup_{banco}_{timestamp}.sql')
            
            # Comando pg_dump
            dump_cmd = f'PGPASSWORD="{senha}" pg_dump -h {host} -p {porta} -U {usuario} -d {banco} -f {backup_file}'
            
            print(f"Criando backup do banco de dados em {backup_file}...")
            exitcode = os.system(dump_cmd)
            
            if exitcode == 0:
                print(f"Backup criado com sucesso em {backup_file}")
                return backup_file
            else:
                print(f"Erro ao criar backup. Código de saída: {exitcode}")
                return None
        else:
            print("Erro: Apenas bancos PostgreSQL são suportados para backup automático.")
            return None
            
    except Exception as e:
        print(f"Erro ao criar backup: {str(e)}")
        return None

def migrar_banco():
    """
    Realiza a migração do banco de dados aplicando as alterações dos modelos
    """
    try:
        print("Iniciando migração do banco de dados...")
        
        # Cria um backup antes de migrar
        backup_file = criar_backup()
        if not backup_file:
            if not confirmar("Não foi possível criar um backup. Deseja continuar mesmo assim?"):
                print("Migração cancelada pelo usuário.")
                return False
        
        # Inicia o contexto da aplicação
        with app.app_context():
            print("Criando tabelas que não existem...")
            db.create_all()
            print("Tabelas criadas/atualizadas com sucesso.")
            
            # Aqui poderia ser implementada uma lógica mais avançada de migração
            # como adicionar colunas a tabelas existentes, alterar tipos, etc.
            # Por enquanto, apenas criamos tabelas que não existem.
            
            print("Migração concluída com sucesso!")
            return True
            
    except Exception as e:
        print(f"Erro durante a migração: {str(e)}")
        return False

def restaurar_backup(backup_file):
    """
    Restaura um backup do banco de dados
    
    Args:
        backup_file: Caminho para o arquivo de backup
    
    Returns:
        bool: True se a restauração for bem-sucedida, False caso contrário
    """
    try:
        conn_string = app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if not conn_string:
            print("Erro: Não foi possível determinar a string de conexão com o banco de dados.")
            return False
        
        # Extrai informações da string de conexão
        if conn_string.startswith('postgresql://'):
            # Remove 'postgresql://'
            conn_info = conn_string[13:]
            
            # Separa usuário:senha@host:porta/banco
            auth_host_db = conn_info.split('@')
            auth = auth_host_db[0]
            host_db = auth_host_db[1]
            
            # Separa usuário:senha
            auth_parts = auth.split(':')
            usuario = auth_parts[0]
            senha = auth_parts[1]
            
            # Separa host:porta/banco
            host_port_db = host_db.split('/')
            host_port = host_port_db[0]
            banco = host_port_db[1]
            
            # Separa host:porta
            host_parts = host_port.split(':')
            host = host_parts[0]
            porta = host_parts[1] if len(host_parts) > 1 else '5432'
            
            # Limpa o banco para restauração
            clean_cmd = f'PGPASSWORD="{senha}" psql -h {host} -p {porta} -U {usuario} -d {banco} -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
            print("Limpando banco de dados para restauração...")
            os.system(clean_cmd)
            
            # Comando pg_restore
            restore_cmd = f'PGPASSWORD="{senha}" psql -h {host} -p {porta} -U {usuario} -d {banco} -f {backup_file}'
            
            print(f"Restaurando backup de {backup_file}...")
            exitcode = os.system(restore_cmd)
            
            if exitcode == 0:
                print("Backup restaurado com sucesso!")
                return True
            else:
                print(f"Erro ao restaurar backup. Código de saída: {exitcode}")
                return False
        else:
            print("Erro: Apenas bancos PostgreSQL são suportados para restauração automática.")
            return False
            
    except Exception as e:
        print(f"Erro ao restaurar backup: {str(e)}")
        return False

def listar_backups():
    """
    Lista todos os backups disponíveis
    
    Returns:
        list: Lista de caminhos para arquivos de backup
    """
    backup_dir = os.path.join(script_dir, 'backups')
    
    if not os.path.exists(backup_dir):
        print("Diretório de backups não encontrado.")
        return []
    
    backups = [f for f in os.listdir(backup_dir) if f.startswith('backup_') and f.endswith('.sql')]
    
    if not backups:
        print("Nenhum backup encontrado.")
        return []
    
    print("Backups disponíveis:")
    for i, backup in enumerate(backups, 1):
        # Extrai informações do nome do arquivo: backup_nome-do-banco_timestamp.sql
        parts = backup.split('_')
        if len(parts) >= 3:
            banco = parts[1]
            timestamp = parts[2].split('.')[0]  # Remove a extensão .sql
            
            # Formata o timestamp
            try:
                data = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                data_formatada = data.strftime('%d/%m/%Y %H:%M:%S')
                print(f"{i}. Banco: {banco}, Data: {data_formatada}, Arquivo: {backup}")
            except:
                print(f"{i}. {backup}")
        else:
            print(f"{i}. {backup}")
    
    return [os.path.join(backup_dir, b) for b in backups]

def confirmar(mensagem):
    """
    Solicita confirmação do usuário
    
    Args:
        mensagem: Mensagem a ser exibida
    
    Returns:
        bool: True se o usuário confirmar, False caso contrário
    """
    resposta = input(f"{mensagem} (s/n): ").lower()
    return resposta == 's' or resposta == 'sim'

def main():
    """Função principal do script"""
    parser = argparse.ArgumentParser(description='Ferramenta de migração de banco de dados')
    
    # Subcomandos
    subparsers = parser.add_subparsers(dest='comando', help='Comandos disponíveis')
    
    # Comando 'migrar'
    parser_migrar = subparsers.add_parser('migrar', help='Migra o banco de dados aplicando alterações dos modelos')
    
    # Comando 'backup'
    parser_backup = subparsers.add_parser('backup', help='Cria um backup do banco de dados')
    
    # Comando 'restaurar'
    parser_restaurar = subparsers.add_parser('restaurar', help='Restaura um backup do banco de dados')
    parser_restaurar.add_argument('-f', '--file', help='Arquivo de backup específico para restaurar')
    
    # Comando 'listar'
    parser_listar = subparsers.add_parser('listar', help='Lista os backups disponíveis')
    
    # Processa os argumentos
    args = parser.parse_args()
    
    # Se nenhum comando for especificado, mostra ajuda
    if not args.comando:
        parser.print_help()
        return
    
    # Executa o comando especificado
    if args.comando == 'migrar':
        migrar_banco()
    
    elif args.comando == 'backup':
        criar_backup()
    
    elif args.comando == 'restaurar':
        if args.file:
            # Restaurar backup específico
            if os.path.exists(args.file):
                if confirmar(f"Tem certeza que deseja restaurar o backup {args.file}?"):
                    restaurar_backup(args.file)
            else:
                print(f"Erro: Arquivo de backup {args.file} não encontrado.")
        else:
            # Solicitar escolha de backup
            backups = listar_backups()
            if backups:
                escolha = input("Digite o número do backup que deseja restaurar (ou 'q' para cancelar): ")
                if escolha.lower() != 'q':
                    try:
                        indice = int(escolha) - 1
                        if 0 <= indice < len(backups):
                            if confirmar(f"Tem certeza que deseja restaurar o backup {os.path.basename(backups[indice])}?"):
                                restaurar_backup(backups[indice])
                        else:
                            print("Número de backup inválido.")
                    except ValueError:
                        print("Entrada inválida. Digite um número válido.")
    
    elif args.comando == 'listar':
        listar_backups()

if __name__ == "__main__":
    main()