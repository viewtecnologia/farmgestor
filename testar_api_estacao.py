#!/usr/bin/env python3
"""
Script para testar a API de estações meteorológicas do RuralSys

Este script simula o envio de dados de uma estação meteorológica para o sistema,
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

# Estações meteorológicas disponíveis
ESTACOES = {
    'EST001': 'Estação Central',
    'EST002': 'Estação Pasto Sul'
}

def enviar_leitura(codigo_estacao, metodo="POST", continuo=False, intervalo=5):
    """
    Envia dados de leitura meteorológica para a API
    
    Args:
        codigo_estacao: Código da estação (ex: EST001)
        metodo: Método HTTP (POST ou GET)
        continuo: Se True, envia dados continuamente
        intervalo: Intervalo entre envios (segundos)
    """
    if codigo_estacao not in ESTACOES:
        print(f"Erro: Estação {codigo_estacao} não encontrada.")
        print(f"Estações disponíveis: {', '.join(ESTACOES.keys())}")
        return False
    
    url = f"{BASE_URL}/api/estacao/leitura"
    
    tentativas = 1 if not continuo else 9999
    
    for _ in range(tentativas):
        # Gerar dados meteorológicos simulados
        temperatura = round(random.uniform(15, 35), 1)
        umidade = round(random.uniform(40, 95), 1)
        pressao = round(random.uniform(1000, 1025), 1)
        vento = round(random.uniform(0, 60), 1)
        direcao_vento = round(random.uniform(0, 359))
        precipitacao = round(random.uniform(0, 10), 1) if random.random() > 0.7 else 0
        bateria = round(random.uniform(70, 100), 1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if metodo == "POST":
            dados = {
                "estacao_id": codigo_estacao,
                "temp": temperatura,
                "umid": umidade,
                "press": pressao,
                "vento": vento,
                "dir_vento": direcao_vento,
                "precip": precipitacao,
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
                "estacao_id": codigo_estacao,
                "temp": temperatura,
                "umid": umidade,
                "press": pressao,
                "vento": vento,
                "dir_vento": direcao_vento,
                "precip": precipitacao,
                "bat": bateria,
                "tkn": API_TOKEN
            }
            
            url_completa = f"{url}?estacao_id={codigo_estacao}&temp={temperatura}&umid={umidade}&press={pressao}&vento={vento}&dir_vento={direcao_vento}&precip={precipitacao}&bat={bateria}&tkn={API_TOKEN}"
            print(f"[{timestamp}] Enviando via GET: URL muito longa, omitindo...")
            
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

def listar_estacoes():
    """Lista todas as estações disponíveis para teste"""
    print("\nEstações meteorológicas disponíveis para teste:")
    print("-" * 50)
    print(f"{'Código':<10} {'Nome':<40}")
    print("-" * 50)
    
    for codigo, nome in ESTACOES.items():
        print(f"{codigo:<10} {nome}")
    
    print("-" * 50)

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Teste da API de Estações Meteorológicas do RuralSys')
    parser.add_argument('--estacao', help='Código da estação (ex: EST001)', default=None)
    parser.add_argument('--listar', action='store_true', help='Lista todas as estações disponíveis')
    parser.add_argument('--metodo', choices=['POST', 'GET'], default='POST', help='Método HTTP (POST ou GET)')
    parser.add_argument('--continuo', action='store_true', help='Envio contínuo de dados')
    parser.add_argument('--intervalo', type=int, default=5, help='Intervalo entre envios (segundos)')
    
    args = parser.parse_args()
    
    if args.listar:
        listar_estacoes()
        return
    
    if not args.estacao:
        # Se nenhuma estação for especificada, usa a primeira da lista
        args.estacao = list(ESTACOES.keys())[0]
        print(f"Nenhuma estação especificada. Usando {args.estacao} por padrão.")
    
    print(f"\n=== TESTE DA API DE ESTAÇÕES METEOROLÓGICAS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    print(f"Estação: {args.estacao} ({ESTACOES.get(args.estacao, 'Desconhecida')})")
    print(f"Método: {args.metodo}")
    print(f"Modo: {'Contínuo' if args.continuo else 'Único'}")
    if args.continuo:
        print(f"Intervalo: {args.intervalo} segundos")
    print("-" * 50)
    
    enviar_leitura(args.estacao, args.metodo, args.continuo, args.intervalo)
    
    if not args.continuo:
        print("\n=== TESTE CONCLUÍDO ===")

if __name__ == "__main__":
    main()