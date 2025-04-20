"""
Script para testar as APIs LoRa e Balanças

Esse script envia requisições para as APIs de LoRa e balanças para 
demonstrar e testar a funcionalidade.
"""

import json
import requests
import random
from datetime import datetime

# Configuração base
BASE_URL = "http://localhost:5000"  # Altere para o endereço correto do servidor
TOKEN_API = "seu-token-de-api-aqui"  # Insira o token de API válido da propriedade

def testar_api_localizacao_post():
    """Teste da API de localização LoRa via POST"""
    print("\n----- Testando API de Localização LoRa (POST) -----")
    
    # Dados para enviar
    dados = {
        "id": "BRINCO123",  # Substitua pelo ID de dispositivo válido
        "lat": -22.9064 + random.uniform(-0.01, 0.01),
        "lon": -47.0616 + random.uniform(-0.01, 0.01),
        "bat": 95.5 - random.uniform(0, 5),
        "tkn": TOKEN_API
    }
    
    # Enviar requisição
    url = f"{BASE_URL}/api/lora/localizacao"
    print(f"Enviando requisição POST para {url}")
    print(f"Dados: {json.dumps(dados, indent=2)}")
    
    try:
        resposta = requests.post(url, json=dados)
        print(f"Status: {resposta.status_code}")
        print(f"Resposta: {json.dumps(resposta.json(), indent=2)}")
    except Exception as e:
        print(f"Erro: {str(e)}")

def testar_api_localizacao_get():
    """Teste da API de localização LoRa via GET"""
    print("\n----- Testando API de Localização LoRa (GET) -----")
    
    # Parâmetros da URL
    params = {
        "id": "BRINCO123",  # Substitua pelo ID de dispositivo válido
        "lat": -22.9064 + random.uniform(-0.01, 0.01),
        "lon": -47.0616 + random.uniform(-0.01, 0.01),
        "bat": 95.5 - random.uniform(0, 5),
        "tkn": TOKEN_API
    }
    
    # Construir URL com parâmetros
    url = f"{BASE_URL}/api/lora/localizacao/get"
    print(f"Enviando requisição GET para {url}")
    print(f"Parâmetros: {params}")
    
    try:
        resposta = requests.get(url, params=params)
        print(f"Status: {resposta.status_code}")
        print(f"Resposta: {json.dumps(resposta.json(), indent=2)}")
    except Exception as e:
        print(f"Erro: {str(e)}")

def testar_api_balanca_post():
    """Teste da API de pesagem de balança via POST"""
    print("\n----- Testando API de Pesagem de Balança (POST) -----")
    
    # Dados para enviar
    dados = {
        "balanca_id": "BAL001",  # Substitua pelo ID de balança válido
        "animal_id": "BOV001",   # Substitua pelo ID de animal válido
        "peso": 450.5 + random.uniform(-10, 10),
        "bat": 98.5 - random.uniform(0, 3),
        "tkn": TOKEN_API
    }
    
    # Enviar requisição
    url = f"{BASE_URL}/api/balanca/pesagem"
    print(f"Enviando requisição POST para {url}")
    print(f"Dados: {json.dumps(dados, indent=2)}")
    
    try:
        resposta = requests.post(url, json=dados)
        print(f"Status: {resposta.status_code}")
        print(f"Resposta: {json.dumps(resposta.json(), indent=2)}")
    except Exception as e:
        print(f"Erro: {str(e)}")

def testar_api_balanca_get():
    """Teste da API de pesagem de balança via GET"""
    print("\n----- Testando API de Pesagem de Balança (GET) -----")
    
    # Parâmetros da URL
    params = {
        "balanca_id": "BAL001",  # Substitua pelo ID de balança válido
        "animal_id": "BOV001",   # Substitua pelo ID de animal válido
        "peso": 450.5 + random.uniform(-10, 10),
        "bat": 98.5 - random.uniform(0, 3),
        "tkn": TOKEN_API
    }
    
    # Construir URL com parâmetros
    url = f"{BASE_URL}/api/balanca/pesagem/get"
    print(f"Enviando requisição GET para {url}")
    print(f"Parâmetros: {params}")
    
    try:
        resposta = requests.get(url, params=params)
        print(f"Status: {resposta.status_code}")
        print(f"Resposta: {json.dumps(resposta.json(), indent=2)}")
    except Exception as e:
        print(f"Erro: {str(e)}")

def testar_api_estacao_post():
    """Teste da API de leitura de estação meteorológica via POST"""
    print("\n----- Testando API de Leitura de Estação Meteorológica (POST) -----")
    
    # Dados para enviar
    dados = {
        "estacao_id": "EST001",  # Substitua pelo ID de estação válido
        "temp": 22.5 + random.uniform(-3, 3),
        "umid": 65.0 + random.uniform(-10, 10),
        "press": 1013.0 + random.uniform(-5, 5),
        "precip": random.uniform(0, 3) if random.random() > 0.7 else 0,
        "vento": random.uniform(0, 20),
        "dir_vento": random.uniform(0, 360),
        "bat": 95.0 - random.uniform(0, 5),
        "tkn": TOKEN_API
    }
    
    # Enviar requisição
    url = f"{BASE_URL}/api/estacao/leitura"
    print(f"Enviando requisição POST para {url}")
    print(f"Dados: {json.dumps(dados, indent=2)}")
    
    try:
        resposta = requests.post(url, json=dados)
        print(f"Status: {resposta.status_code}")
        print(f"Resposta: {json.dumps(resposta.json(), indent=2)}")
    except Exception as e:
        print(f"Erro: {str(e)}")

def testar_api_estacao_get():
    """Teste da API de leitura de estação meteorológica via GET"""
    print("\n----- Testando API de Leitura de Estação Meteorológica (GET) -----")
    
    # Parâmetros da URL
    params = {
        "estacao_id": "EST001",  # Substitua pelo ID de estação válido
        "temp": 22.5 + random.uniform(-3, 3),
        "umid": 65.0 + random.uniform(-10, 10),
        "press": 1013.0 + random.uniform(-5, 5),
        "precip": random.uniform(0, 3) if random.random() > 0.7 else 0,
        "vento": random.uniform(0, 20),
        "dir_vento": random.uniform(0, 360),
        "bat": 95.0 - random.uniform(0, 5),
        "tkn": TOKEN_API
    }
    
    # Construir URL com parâmetros
    url = f"{BASE_URL}/api/estacao/leitura"
    print(f"Enviando requisição GET para {url}")
    print(f"Parâmetros: {params}")
    
    try:
        resposta = requests.get(url, params=params)
        print(f"Status: {resposta.status_code}")
        print(f"Resposta: {json.dumps(resposta.json(), indent=2)}")
    except Exception as e:
        print(f"Erro: {str(e)}")

def executar_todos_testes():
    """Executa todos os testes da API"""
    print("\n===== INÍCIO DOS TESTES DE API =====")
    print(f"URL Base: {BASE_URL}")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    testar_api_localizacao_post()
    testar_api_localizacao_get()
    testar_api_balanca_post()
    testar_api_balanca_get()
    testar_api_estacao_post()
    testar_api_estacao_get()
    
    print("\n===== FIM DOS TESTES DE API =====")

if __name__ == "__main__":
    executar_todos_testes()