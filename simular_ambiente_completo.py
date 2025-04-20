#!/usr/bin/env python3
"""
Simulador de Ambiente Rural Completo para RuralSys

Este script simula um ambiente rural completo com múltiplos dispositivos enviando
dados simultaneamente, incluindo:
- Dispositivos LoRa de rastreamento de animais
- Balanças digitais de pesagem
- Estações meteorológicas

Ideal para demonstração e testes de carga do sistema RuralSys.
"""
import argparse
import json
import random
import requests
import time
import threading
from datetime import datetime

# Configurações
API_TOKEN = "79e0d05b5e2721d69ee9a5122abbfd5491fdabb5f10cb3b0e6c17bfefaa2bcab"  # Token API da Fazenda Modelo
BASE_URL = "http://localhost:5000"  # URL base do sistema

# Cores para output no terminal
class Cores:
    VERDE = '\033[92m'
    AZUL = '\033[94m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    MAGENTA = '\033[95m'
    CIANO = '\033[96m'
    RESET = '\033[0m'
    NEGRITO = '\033[1m'

# Dispositivos disponíveis
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

ESTACOES = {
    'EST001': 'Estação Central',
    'EST002': 'Estação Pasto Sul'
}

# Coordenadas base da fazenda (exemplo)
LAT_BASE = -22.9064
LON_BASE = -47.0616

# Funções de simulação
def simular_dispositivo_lora(codigo_animal, intervalo=5, parar_evento=None):
    """Simula um dispositivo LoRa enviando localizações"""
    url = f"{BASE_URL}/api/lora/localizacao"
    
    print(f"{Cores.VERDE}[LoRa] Iniciando simulação para animal: {codigo_animal}{Cores.RESET}")
    
    contador = 0
    while not parar_evento.is_set():
        contador += 1
        # Gerar coordenadas com variação aleatória
        lat = LAT_BASE + random.uniform(-0.01, 0.01)
        lon = LON_BASE + random.uniform(-0.01, 0.01)
        bateria = round(random.uniform(80, 100), 1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        dados = {
            "id": codigo_animal,
            "lat": lat,
            "lon": lon,
            "bat": bateria,
            "tkn": API_TOKEN
        }
        
        print(f"{Cores.VERDE}[LoRa][{timestamp}] Animal {codigo_animal}: Enviando localização (Lat: {lat:.6f}, Lon: {lon:.6f}){Cores.RESET}")
        
        try:
            resposta = requests.post(url, json=dados, timeout=5)
            if resposta.status_code == 200:
                print(f"{Cores.VERDE}[LoRa] Animal {codigo_animal}: Localização recebida com sucesso!{Cores.RESET}")
            else:
                print(f"{Cores.VERMELHO}[LoRa] Animal {codigo_animal}: Erro HTTP {resposta.status_code} - {resposta.text}{Cores.RESET}")
        except Exception as e:
            print(f"{Cores.VERMELHO}[LoRa] Animal {codigo_animal}: Falha ao enviar dados - {str(e)}{Cores.RESET}")
        
        # Pausar entre envios (com verificação de parada a cada segundo)
        for _ in range(intervalo):
            if parar_evento.is_set():
                break
            time.sleep(1)
            
    print(f"{Cores.VERDE}[LoRa] Simulação encerrada para animal: {codigo_animal} após {contador} envios{Cores.RESET}")

def simular_balanca_digital(codigo_balanca, codigo_animal, intervalo=30, parar_evento=None):
    """Simula uma balança digital enviando pesagens"""
    url = f"{BASE_URL}/api/balanca/pesagem"
    
    print(f"{Cores.AZUL}[Balança] Iniciando simulação para balança: {codigo_balanca} e animal: {codigo_animal}{Cores.RESET}")
    
    contador = 0
    while not parar_evento.is_set():
        contador += 1
        # Gerar peso com variação aleatória
        peso = round(random.uniform(350, 650), 1)
        bateria = round(random.uniform(80, 100), 1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        dados = {
            "balanca_id": codigo_balanca,
            "animal_id": codigo_animal,
            "peso": peso,
            "bat": bateria,
            "tkn": API_TOKEN
        }
        
        print(f"{Cores.AZUL}[Balança][{timestamp}] Balança {codigo_balanca}: Registrando peso de {peso}kg para animal {codigo_animal}{Cores.RESET}")
        
        try:
            resposta = requests.post(url, json=dados, timeout=5)
            if resposta.status_code == 200:
                print(f"{Cores.AZUL}[Balança] Balança {codigo_balanca}: Pesagem registrada com sucesso!{Cores.RESET}")
            else:
                print(f"{Cores.VERMELHO}[Balança] Balança {codigo_balanca}: Erro HTTP {resposta.status_code} - {resposta.text}{Cores.RESET}")
        except Exception as e:
            print(f"{Cores.VERMELHO}[Balança] Balança {codigo_balanca}: Falha ao enviar dados - {str(e)}{Cores.RESET}")
        
        # Pausar entre envios (com verificação de parada a cada segundo)
        for _ in range(intervalo):
            if parar_evento.is_set():
                break
            time.sleep(1)
            
    print(f"{Cores.AZUL}[Balança] Simulação encerrada para balança: {codigo_balanca} após {contador} envios{Cores.RESET}")

def simular_estacao_meteorologica(codigo_estacao, intervalo=60, parar_evento=None):
    """Simula uma estação meteorológica enviando leituras"""
    url = f"{BASE_URL}/api/estacao/leitura"
    
    print(f"{Cores.AMARELO}[Estação] Iniciando simulação para estação: {codigo_estacao}{Cores.RESET}")
    
    contador = 0
    while not parar_evento.is_set():
        contador += 1
        # Gerar dados meteorológicos simulados
        temperatura = round(random.uniform(15, 35), 1)
        umidade = round(random.uniform(40, 95), 1)
        pressao = round(random.uniform(1000, 1025), 1)
        vento = round(random.uniform(0, 60), 1)
        direcao_vento = round(random.uniform(0, 359))
        precipitacao = round(random.uniform(0, 10), 1) if random.random() > 0.7 else 0
        bateria = round(random.uniform(70, 100), 1)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
        
        print(f"{Cores.AMARELO}[Estação][{timestamp}] Estação {codigo_estacao}: Temperatura: {temperatura}°C, Umidade: {umidade}%, Precipitação: {precipitacao}mm{Cores.RESET}")
        
        try:
            resposta = requests.post(url, json=dados, timeout=5)
            if resposta.status_code == 200:
                print(f"{Cores.AMARELO}[Estação] Estação {codigo_estacao}: Leitura registrada com sucesso!{Cores.RESET}")
            else:
                print(f"{Cores.VERMELHO}[Estação] Estação {codigo_estacao}: Erro HTTP {resposta.status_code} - {resposta.text}{Cores.RESET}")
        except Exception as e:
            print(f"{Cores.VERMELHO}[Estação] Estação {codigo_estacao}: Falha ao enviar dados - {str(e)}{Cores.RESET}")
        
        # Pausar entre envios (com verificação de parada a cada segundo)
        for _ in range(intervalo):
            if parar_evento.is_set():
                break
            time.sleep(1)
            
    print(f"{Cores.AMARELO}[Estação] Simulação encerrada para estação: {codigo_estacao} após {contador} envios{Cores.RESET}")

def iniciar_simulacao(duracao=300, animais=None, balancas=None, estacoes=None):
    """Inicia a simulação completa com todos os dispositivos selecionados"""
    if animais is None:
        animais = list(ANIMAIS.keys())
    if balancas is None:
        balancas = list(BALANCAS.keys())
    if estacoes is None:
        estacoes = list(ESTACOES.keys())
    
    # Evento para parar as threads
    parar_evento = threading.Event()
    threads = []
    
    try:
        # Iniciar threads de dispositivos LoRa
        for animal in animais:
            t = threading.Thread(target=simular_dispositivo_lora, args=(animal, random.randint(10, 20), parar_evento))
            t.daemon = True
            threads.append(t)
            t.start()
            time.sleep(1)  # Intervalo entre inicialização de dispositivos
        
        # Iniciar threads de balanças
        for balanca in balancas:
            # Seleciona um animal aleatório para cada balança
            animal = random.choice(animais)
            t = threading.Thread(target=simular_balanca_digital, args=(balanca, animal, random.randint(25, 35), parar_evento))
            t.daemon = True
            threads.append(t)
            t.start()
            time.sleep(1)
        
        # Iniciar threads de estações
        for estacao in estacoes:
            t = threading.Thread(target=simular_estacao_meteorologica, args=(estacao, random.randint(40, 60), parar_evento))
            t.daemon = True
            threads.append(t)
            t.start()
            time.sleep(1)
        
        print(f"\n{Cores.NEGRITO}{'='*80}{Cores.RESET}")
        print(f"{Cores.NEGRITO}SIMULAÇÃO INICIADA COM {len(threads)} DISPOSITIVOS{Cores.RESET}")
        print(f"{Cores.NEGRITO}  - {len(animais)} dispositivos LoRa{Cores.RESET}")
        print(f"{Cores.NEGRITO}  - {len(balancas)} balanças digitais{Cores.RESET}")
        print(f"{Cores.NEGRITO}  - {len(estacoes)} estações meteorológicas{Cores.RESET}")
        print(f"{Cores.NEGRITO}Duração: {duracao} segundos{Cores.RESET}")
        print(f"{Cores.NEGRITO}{'='*80}{Cores.RESET}\n")
        
        # Contagem regressiva
        inicio = time.time()
        while time.time() - inicio < duracao:
            tempo_restante = int(duracao - (time.time() - inicio))
            if tempo_restante % 30 == 0 or tempo_restante <= 10:
                print(f"{Cores.MAGENTA}[Sistema] Tempo restante: {tempo_restante} segundos{Cores.RESET}")
            time.sleep(1)
        
        # Encerrar threads
        print(f"\n{Cores.NEGRITO}{Cores.MAGENTA}[Sistema] Encerrando simulação...{Cores.RESET}")
        parar_evento.set()
        
        # Aguardar até 5 segundos para as threads terminarem
        for t in threads:
            t.join(timeout=5)
            
        print(f"\n{Cores.NEGRITO}{'='*80}{Cores.RESET}")
        print(f"{Cores.NEGRITO}SIMULAÇÃO CONCLUÍDA{Cores.RESET}")
        print(f"{Cores.NEGRITO}{'='*80}{Cores.RESET}\n")
        
    except KeyboardInterrupt:
        print(f"\n{Cores.VERMELHO}[Sistema] Interrupção do usuário. Encerrando simulação...{Cores.RESET}")
        parar_evento.set()
        
        # Aguardar até 5 segundos para as threads terminarem
        for t in threads:
            t.join(timeout=5)
            
        print(f"\n{Cores.NEGRITO}{'='*80}{Cores.RESET}")
        print(f"{Cores.NEGRITO}SIMULAÇÃO INTERROMPIDA{Cores.RESET}")
        print(f"{Cores.NEGRITO}{'='*80}{Cores.RESET}\n")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Simulador de Ambiente Rural Completo para RuralSys')
    parser.add_argument('--duracao', type=int, default=300, help='Duração da simulação em segundos (padrão: 300s)')
    parser.add_argument('--animais', type=int, default=3, help='Número de animais para simular (padrão: 3)')
    parser.add_argument('--balancas', type=int, default=1, help='Número de balanças para simular (padrão: 1)')
    parser.add_argument('--estacoes', type=int, default=2, help='Número de estações para simular (padrão: 2)')
    
    args = parser.parse_args()
    
    # Selecionar dispositivos aleatórios com base na quantidade solicitada
    animais_select = random.sample(list(ANIMAIS.keys()), min(args.animais, len(ANIMAIS)))
    balancas_select = random.sample(list(BALANCAS.keys()), min(args.balancas, len(BALANCAS)))
    estacoes_select = random.sample(list(ESTACOES.keys()), min(args.estacoes, len(ESTACOES)))
    
    print(f"\n{Cores.NEGRITO}SIMULADOR DE AMBIENTE RURAL COMPLETO PARA RURALSYS{Cores.RESET}")
    print(f"{Cores.NEGRITO}{'='*80}{Cores.RESET}")
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"URL Base: {BASE_URL}\n")
    
    print("Configuração da simulação:")
    print(f"- Duração: {args.duracao} segundos")
    print(f"- Animais: {args.animais} ({', '.join(animais_select)})")
    print(f"- Balanças: {args.balancas} ({', '.join(balancas_select)})")
    print(f"- Estações: {args.estacoes} ({', '.join(estacoes_select)})")
    print(f"{Cores.NEGRITO}{'='*80}{Cores.RESET}\n")
    
    iniciar_simulacao(args.duracao, animais_select, balancas_select, estacoes_select)

if __name__ == "__main__":
    main()