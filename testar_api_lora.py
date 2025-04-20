#!/usr/bin/env python3
"""
Script para testar a API de integração LoRa do RuralSys

Este script simula o envio de dados de um dispositivo LoRa para o sistema,
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
DISPOSITIVOS = {
    'BOV004': '967caea9-952b-4db5-aebd-333555627c80',
    'BOV005': '96e1b08f-19c4-46c6-a700-cccbd05b8256',
    'BOV006': 'e39f2a76-3468-46c2-8624-2a907be99535',
    'BOV007': 'f7feff42-84fd-4273-be30-ef9f2081076a',
    'BOV008': 'd511b6f9-ce70-4780-bcd9-a46dfa686958'
}

# Coordenadas base da fazenda (exemplo)
LAT_BASE = -22.9064
LON_BASE = -47.0616

def enviar_localizacao(codigo_animal, metodo="POST", continuo=False, intervalo=5):
    """
    Envia dados de localização para a API
    
    Args:
        codigo_animal: Código do animal (ex: BOV004)
        metodo: Método HTTP (POST ou GET)
        continuo: Se True, envia dados continuamente
        intervalo: Intervalo entre envios (segundos)
    """
    if codigo_animal not in DISPOSITIVOS:
        print(f"Erro: Animal {codigo_animal} não encontrado.")
        print(f"Animais disponíveis: {', '.join(DISPOSITIVOS.keys())}")
        return False
    
    url = f"{BASE_URL}/api/lora/localizacao"
    if metodo == "GET":
        url = f"{BASE_URL}/api/lora/localizacao/get"
    
    tentativas = 1 if not continuo else 9999
    
    for _ in range(tentativas):
        # Gerar coordenadas com variação aleatória
        lat = LAT_BASE + random.uniform(-0.01, 0.01)
        lon = LON_BASE + random.uniform(-0.01, 0.01)
        bateria = round(random.uniform(80, 100), 1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if metodo == "POST":
            dados = {
                "id": codigo_animal,
                "lat": lat,
                "lon": lon,
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
                "id": codigo_animal,
                "lat": lat,
                "lon": lon,
                "bat": bateria,
                "tkn": API_TOKEN
            }
            
            url_completa = f"{url}?id={codigo_animal}&lat={lat}&lon={lon}&bat={bateria}&tkn={API_TOKEN}"
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

def listar_animais():
    """Lista todos os animais disponíveis para teste"""
    print("\nAnimais disponíveis para teste:")
    print("-" * 50)
    print(f"{'Código':<10} {'ID do Dispositivo':<40}")
    print("-" * 50)
    
    for codigo, dispositivo_id in DISPOSITIVOS.items():
        print(f"{codigo:<10} {dispositivo_id}")
    
    print("-" * 50)

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Teste da API LoRa do RuralSys')
    parser.add_argument('--animal', help='Código do animal (ex: BOV004)', default=None)
    parser.add_argument('--listar', action='store_true', help='Lista todos os animais disponíveis')
    parser.add_argument('--metodo', choices=['POST', 'GET'], default='POST', help='Método HTTP (POST ou GET)')
    parser.add_argument('--continuo', action='store_true', help='Envio contínuo de dados')
    parser.add_argument('--intervalo', type=int, default=5, help='Intervalo entre envios (segundos)')
    
    args = parser.parse_args()
    
    if args.listar:
        listar_animais()
        return
    
    if not args.animal:
        # Se nenhum animal for especificado, usa o primeiro da lista
        args.animal = list(DISPOSITIVOS.keys())[0]
        print(f"Nenhum animal especificado. Usando {args.animal} por padrão.")
    
    print(f"\n=== TESTE DA API LORA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    print(f"Animal: {args.animal}")
    print(f"Método: {args.metodo}")
    print(f"Modo: {'Contínuo' if args.continuo else 'Único'}")
    if args.continuo:
        print(f"Intervalo: {args.intervalo} segundos")
    print("-" * 50)
    
    enviar_localizacao(args.animal, args.metodo, args.continuo, args.intervalo)
    
    if not args.continuo:
        print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    main()