import logging
import json
from datetime import datetime
import time
import random
from models import Animal, HistoricoLocalizacao, DispositivoLora
from app import db

# Configuração de logging
logger = logging.getLogger(__name__)

class LoRaManager:
    """
    Classe responsável pela comunicação com dispositivos LoRa.
    
    Em um sistema real, esta classe implementaria a comunicação com
    um gateway LoRa usando bibliotecas específicas. Nesta versão,
    simulamos o comportamento para fins de demonstração.
    """
    
    def __init__(self):
        self.gateway_connected = False
    
    def connect_to_gateway(self):
        """Simula conexão com gateway LoRa"""
        logger.info("Conectando ao gateway LoRa...")
        # Em um sistema real, aqui seria implementada a conexão com o gateway
        self.gateway_connected = True
        logger.info("Conexão com gateway LoRa estabelecida")
        return self.gateway_connected
    
    def disconnect_gateway(self):
        """Desconecta do gateway LoRa"""
        if self.gateway_connected:
            logger.info("Desconectando do gateway LoRa...")
            self.gateway_connected = False
            logger.info("Gateway LoRa desconectado")
    
    def send_command(self, device_id, command):
        """
        Envia um comando para um dispositivo específico
        
        Args:
            device_id (str): ID do dispositivo
            command (dict): Comando a ser enviado
        
        Returns:
            bool: Sucesso do envio
        """
        if not self.gateway_connected:
            logger.error("Gateway LoRa não está conectado")
            return False
        
        logger.info(f"Enviando comando para dispositivo {device_id}: {command}")
        # Em um sistema real, aqui seria implementado o envio do comando
        
        return True
    
    def request_location(self, device_id):
        """
        Solicita a localização atual de um dispositivo
        
        Args:
            device_id (str): ID do dispositivo
        
        Returns:
            dict: Dados de localização (simulados)
        """
        if not self.gateway_connected:
            logger.error("Gateway LoRa não está conectado")
            return None
        
        logger.info(f"Solicitando localização do dispositivo {device_id}")
        
        # Em um sistema real, aqui seria implementada a solicitação
        # e aguardaria a resposta do dispositivo
        
        # Para demonstração, retornamos dados simulados
        return {
            'device_id': device_id,
            'latitude': random.uniform(-23.5, -23.6),  # Simulação de coordenadas
            'longitude': random.uniform(-46.6, -46.7),
            'battery': random.uniform(50, 100),
            'timestamp': datetime.now().isoformat()
        }

def process_lora_message(message_json):
    """
    Processa uma mensagem recebida de um dispositivo LoRa
    
    Args:
        message_json (str): Mensagem em formato JSON
    
    Returns:
        bool: Sucesso do processamento
    """
    try:
        message = json.loads(message_json)
        device_id = message.get('device_id')
        
        if not device_id:
            logger.error("Mensagem LoRa sem device_id")
            return False
        
        # Buscar o animal associado ao dispositivo
        animal = Animal.query.filter_by(id_dispositivo=device_id).first()
        
        if not animal:
            logger.warning(f"Dispositivo {device_id} não está associado a nenhum animal")
            return False
        
        # Atualizar localização do animal
        if 'latitude' in message and 'longitude' in message:
            animal.ultima_latitude = message['latitude']
            animal.ultima_longitude = message['longitude']
            animal.ultima_atualizacao = datetime.now()
            
            # Atualizar bateria se disponível
            if 'battery' in message:
                animal.bateria = message['battery']
            
            # Registrar no histórico
            historico = HistoricoLocalizacao(
                animal_id=animal.id,
                device_id=device_id,
                latitude=message['latitude'],
                longitude=message['longitude'],
                bateria=message.get('battery', 0)
            )
            
            db.session.add(historico)
            db.session.commit()
            
            logger.info(f"Localização do animal {animal.codigo} atualizada via LoRa")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem LoRa: {str(e)}")
        return False

def simulate_lora_data(num_devices=5):
    """
    Simula dados de localização de dispositivos LoRa para demonstração
    
    Args:
        num_devices (int): Número de dispositivos a simular
    """
    logger.info(f"Simulando dados para {num_devices} dispositivos LoRa")
    
    # Buscar dispositivos ativos
    animais = Animal.query.filter(Animal.id_dispositivo.isnot(None)).limit(num_devices).all()
    
    if not animais:
        logger.warning("Nenhum animal com dispositivo LoRa encontrado")
        return
    
    for animal in animais:
        # Simular uma pequena variação na posição anterior
        if animal.ultima_latitude and animal.ultima_longitude:
            lat = animal.ultima_latitude + random.uniform(-0.002, 0.002)
            lng = animal.ultima_longitude + random.uniform(-0.002, 0.002)
        else:
            # Posição inicial aleatória se não houver posição anterior
            lat = -23.5 + random.uniform(-0.1, 0.1)  # Região central de São Paulo como exemplo
            lng = -46.6 + random.uniform(-0.1, 0.1)
        
        bat = animal.bateria - random.uniform(0, 0.5) if animal.bateria else random.uniform(80, 100)
        
        # Garantir que a bateria não fique negativa
        bat = max(0, bat)
        
        # Criar mensagem simulada
        message = {
            'device_id': animal.id_dispositivo,
            'latitude': lat,
            'longitude': lng,
            'battery': bat,
            'timestamp': datetime.now().isoformat()
        }
        
        # Processar a mensagem simulada
        process_lora_message(json.dumps(message))
    
    logger.info("Simulação de dados LoRa concluída")
