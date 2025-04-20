#!/usr/bin/env python3
"""
Script para gerar automaticamente o arquivo requirements.txt
para uso na construção da imagem Docker.

Este script extrai as dependências do arquivo pyproject.toml
e as escreve em um formato compatível com Docker.
"""

import os
import sys
import tomli
import subprocess

# Lista de pacotes essenciais que devem ser incluídos
PACOTES_ESSENCIAIS = [
    "flask",
    "flask-login",
    "flask-sqlalchemy",
    "flask-wtf",
    "gunicorn",
    "pandas",
    "psycopg2-binary",
    "email-validator",
    "sqlalchemy",
    "werkzeug", 
    "xlsxwriter",
    "python-dotenv"
]

def ler_versoes_instaladas():
    """Lê as versões instaladas dos pacotes utilizando pip freeze."""
    resultado = subprocess.run(
        ["pip", "freeze"], 
        capture_output=True, 
        text=True
    )
    
    if resultado.returncode != 0:
        print("Erro ao executar 'pip freeze'")
        return {}
    
    versoes = {}
    for linha in resultado.stdout.splitlines():
        if "==" in linha:
            pacote, versao = linha.split("==")
            versoes[pacote.lower()] = versao
    
    return versoes

def gerar_requirements():
    """Gera o arquivo requirements.txt com base nos pacotes instalados."""
    versoes = ler_versoes_instaladas()
    
    with open("requirements.txt", "w") as arquivo:
        for pacote in PACOTES_ESSENCIAIS:
            if pacote.lower() in versoes:
                arquivo.write(f"{pacote}=={versoes[pacote.lower()]}\n")
            else:
                arquivo.write(f"{pacote}\n")
    
    print("Arquivo requirements.txt gerado com sucesso!")
    print(f"Total de {len(PACOTES_ESSENCIAIS)} pacotes incluídos.")

if __name__ == "__main__":
    try:
        gerar_requirements()
    except Exception as e:
        print(f"Erro ao gerar requirements.txt: {e}")
        sys.exit(1)