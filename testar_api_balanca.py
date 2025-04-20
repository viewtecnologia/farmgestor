#!/usr/bin/env python3
"""
Script para testar a API de balanças digitais do RuralSys

Este script simula o envio de dados de uma balança digital para o sistema,
permitindo testar o funcionamento da API sem precisar de hardware real.
"""
import argparse
import json
import random
import requests
import time
from datetime import datetime

# Configurações
API_TOKEN = "79e0d05b5e2721d69ee9a5122abbfd5491fdabb5f10cb3b0e6c17bfefaa2bcab"  # Token API da Fazenda Modelo
BASE_URL = "http://localhost:5000"  # URL base do sistema

# IDs dos dispositivos de teste
ANIMAIS = {
    'BOV004': '967caea9-952b-4db5-aebd-333555627c80',
    'BOV005': '96e1b08f-19c4-46c6-a700-cccbd05b8256',
    'BOV006': 'e39f2a76-3468-46c2-8624-2a907be99535',
    'BOV007': 'f7feff42-84fd-4273-be30-ef9f2081076a',
    'BOV008': 'd511b6f9-ce70-4780-bcd9-a46dfa686958'
}

BALANCAS = {
    'BALANCA001': 'Balança Curral'
}

def enviar_pesagem(codigo_animal, codigo_balanca="BALANCA001", metodo="POST", continuo=False, intervalo=5):
    """
    Envia dados de pesagem para a API
    
    Args:
        codigo_animal: Código do animal (ex: BOV004)
        codigo_balanca: Código da balança (ex: BALANCA001)
        metodo: Método HTTP (POST ou GET)
        continuo: Se True, envia dados continuamente
        intervalo: Intervalo entre envios (segundos)
    """
    if codigo_animal not in ANIMAIS:
        print(f"Erro: Animal {codigo_animal} não encontrado.")
        print(f"Animais disponíveis: {', '.join(ANIMAIS.keys())}")
        return False
    
    if codigo_balanca not in BALANCAS:
        print(f"Erro: Balança {codigo_balanca} não encontrada.")
        print(f"Balanças disponíveis: {', '.join(BALANCAS.keys())}")
        return False
    
    url = f"{BASE_URL}/api/balanca/pesagem"
    if metodo == "GET":
        url = f"{BASE_URL}/api/balanca/pesagem/get"
    
    tentativas = 1 if not continuo else 9999
    
    for _ in range(tentativas):
        # Gerar peso com variação aleatória
        peso = round(random.uniform(350, 650), 1)
        bateria = round(random.uniform(80, 100), 1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if metodo == "POST":
            dados = {
                "balanca_id": codigo_balanca,
                "animal_id": codigo_animal,
                "peso": peso,
                "bat": bateria,
                "tkn": API_TOKEN
            }
            
            print(f"[{timestamp}] Enviando via POST: {json.dumps(dados, indent=2)}")
            
            try:
                resposta = requests.post(url, json=dados)
                print(f"Status: {resposta.status_code}")
                print(f"Resposta: {resposta.text}")
            except Exception as e:
                print(f"Erro ao enviar dados: {str(e)}")
        
        else:  # GET
            params = {
                "balanca_id": codigo_balanca,
                "animal_id": codigo_animal,
                "peso": peso,
                "bat": bateria,
                "tkn": API_TOKEN
            }
            
            url_completa = f"{url}?balanca_id={codigo_balanca}&animal_id={codigo_animal}&peso={peso}&bat={bateria}&tkn={API_TOKEN}"
            print(f"[{timestamp}] Enviando via GET: {url_completa}")
            
            try:
                resposta = requests.get(url, params=params)
                print(f"Status: {resposta.status_code}")
                print(f"Resposta: {resposta.text}")
            except Exception as e:
                print(f"Erro ao enviar dados: {str(e)}")
        
        if continuo:
            print(f"\nAguardando {intervalo} segundos até o próximo envio...\n")
            time.sleep(intervalo)
    
    return True

def listar_dispositivos():
    """Lista todos os animais e balanças disponíveis para teste"""
    print("\nAnimais disponíveis para teste:")
    print("-" * 50)
    print(f"{'Código':<10} {'ID do Dispositivo':<40}")
    print("-" * 50)
    
    for codigo, dispositivo_id in ANIMAIS.items():
        print(f"{codigo:<10} {dispositivo_id}")
    
    print("\nBalanças disponíveis para teste:")
    print("-" * 50)
    print(f"{'Código':<10} {'Nome':<40}")
    print("-" * 50)
    
    for codigo, nome in BALANCAS.items():
        print(f"{codigo:<10} {nome}")
    
    print("-" * 50)

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Teste da API de Balanças do RuralSys')
    parser.add_argument('--animal', help='Código do animal (ex: BOV004)', default=None)
    parser.add_argument('--balanca', help='Código da balança (ex: BALANCA001)', default="BALANCA001")
    parser.add_argument('--listar', action='store_true', help='Lista todos os dispositivos disponíveis')
    parser.add_argument('--metodo', choices=['POST', 'GET'], default='POST', help='Método HTTP (POST ou GET)')
    parser.add_argument('--continuo', action='store_true', help='Envio contínuo de dados')
    parser.add_argument('--intervalo', type=int, default=5, help='Intervalo entre envios (segundos)')
    
    args = parser.parse_args()
    
    if args.listar:
        listar_dispositivos()
        return
    
    if not args.animal:
        # Se nenhum animal for especificado, usa o primeiro da lista
        args.animal = list(ANIMAIS.keys())[0]
        print(f"Nenhum animal especificado. Usando {args.animal} por padrão.")
    
    print(f"\n=== TESTE DA API DE BALANÇAS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    print(f"Animal: {args.animal}")
    print(f"Balança: {args.balanca}")
    print(f"Método: {args.metodo}")
    print(f"Modo: {'Contínuo' if args.continuo else 'Único'}")
    if args.continuo:
        print(f"Intervalo: {args.intervalo} segundos")
    print("-" * 50)
    
    enviar_pesagem(args.animal, args.balanca, args.metodo, args.continuo, args.intervalo)
    
    if not args.continuo:
        print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    main()