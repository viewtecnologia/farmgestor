"""
API para recepção de dados de dispositivos LoRa e balanças digitais.

Este módulo implementa endpoints API para receber dados de dispositivos IoT,
como localizadores LoRa de animais, estações meteorológicas e balanças digitais.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from app import db
from models import (
    Propriedade, Animal, HistoricoLocalizacao, RegistroPeso, 
    BalancaDigital, EstacaoMeteorologica, LeituraMeteorologica
)
from lora_communication import process_lora_message

# Configuração de logging
logger = logging.getLogger(__name__)

# Criação do blueprint da API
api_bp = Blueprint('api', __name__, url_prefix='/api')

def verificar_token(token):
    """
    Verifica se o token de autenticação é válido.
    
    Args:
        token (str): Token de API a ser verificado
    
    Returns:
        Propriedade: objeto da propriedade se o token for válido, None caso contrário
    """
    if not token:
        return None
    
    propriedade = Propriedade.query.filter_by(api_token=token).first()
    return propriedade

@api_bp.route('/lora/localizacao', methods=['POST'])
def receber_localizacao_lora():
    """
    Endpoint para receber dados de localização de dispositivos LoRa.
    
    Formato esperado:
    {
        "id": "ID_DISPOSITIVO",
        "lat": LATITUDE,
        "lon": LONGITUDE,
        "bat": BATERIA (opcional),
        "tkn": "TOKEN_API"
    }
    
    Exemplo de chamada:
    POST /api/lora/localizacao
    {
        "id": "BRINCO123",
        "lat": -22.9064,
        "lon": -47.0616,
        "bat": 95.5,
        "tkn": "token-secreto-api"
    }
    """
    try:
        # Obter dados da requisição
        data = request.get_json() or {}
        
        # Validação básica dos campos obrigatórios
        for campo in ['id', 'lat', 'lon', 'tkn']:
            if campo not in data:
                return jsonify({"erro": f"Campo obrigatório ausente: {campo}"}), 400
        
        # Verificar autenticação
        propriedade = verificar_token(data['tkn'])
        if not propriedade:
            return jsonify({"erro": "Token de API inválido"}), 401
        
        # Buscar o animal pelo ID do dispositivo
        animal = Animal.query.filter_by(id_dispositivo=data['id']).first()
        if not animal:
            return jsonify({"erro": f"Dispositivo não encontrado: {data['id']}"}), 404
        
        # Atualizar localização do animal
        animal.ultima_latitude = data['lat']
        animal.ultima_longitude = data['lon']
        animal.ultima_atualizacao = datetime.now()
        
        # Atualizar bateria, se fornecida
        if 'bat' in data:
            animal.bateria = data['bat']
        
        # Registrar no histórico
        historico = HistoricoLocalizacao(
            animal_id=animal.id,
            device_id=data['id'],
            latitude=data['lat'],
            longitude=data['lon'],
            bateria=data.get('bat')
        )
        
        db.session.add(historico)
        db.session.commit()
        
        logger.info(f"Localização recebida via API para animal {animal.codigo}: lat={data['lat']}, lon={data['lon']}")
        
        return jsonify({"status": "sucesso", "animal": animal.codigo})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar localização LoRa: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@api_bp.route('/lora/localizacao/get', methods=['GET'])
def receber_localizacao_lora_get():
    """
    Endpoint para receber dados de localização via GET (mais simples para dispositivos IoT).
    
    Parâmetros de URL:
    - id: ID do dispositivo
    - lat: Latitude
    - lon: Longitude
    - bat: Bateria (opcional)
    - tkn: Token de API
    
    Exemplo:
    GET /api/lora/localizacao/get?id=BRINCO123&lat=-22.9064&lon=-47.0616&bat=95.5&tkn=token-secreto-api
    """
    try:
        # Obter dados da requisição
        device_id = request.args.get('id')
        latitude = request.args.get('lat')
        longitude = request.args.get('lon')
        bateria = request.args.get('bat')
        token = request.args.get('tkn')
        
        # Validação básica dos campos obrigatórios
        if not all([device_id, latitude, longitude, token]):
            return jsonify({"erro": "Parâmetros obrigatórios ausentes"}), 400
        
        # Converter valores
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            bateria = float(bateria) if bateria is not None else None
        except ValueError:
            return jsonify({"erro": "Valores inválidos para latitude/longitude/bateria"}), 400
        
        # Verificar autenticação
        propriedade = verificar_token(token)
        if not propriedade:
            return jsonify({"erro": "Token de API inválido"}), 401
        
        # Buscar o animal pelo ID do dispositivo
        animal = Animal.query.filter_by(id_dispositivo=device_id).first()
        if not animal:
            return jsonify({"erro": f"Dispositivo não encontrado: {device_id}"}), 404
        
        # Atualizar localização do animal
        animal.ultima_latitude = latitude
        animal.ultima_longitude = longitude
        animal.ultima_atualizacao = datetime.now()
        
        # Atualizar bateria, se fornecida
        if bateria is not None:
            animal.bateria = bateria
        
        # Registrar no histórico
        historico = HistoricoLocalizacao(
            animal_id=animal.id,
            device_id=device_id,
            latitude=latitude,
            longitude=longitude,
            bateria=bateria
        )
        
        db.session.add(historico)
        db.session.commit()
        
        logger.info(f"Localização recebida via API GET para animal {animal.codigo}: lat={latitude}, lon={longitude}")
        
        return jsonify({"status": "sucesso", "animal": animal.codigo})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar localização LoRa via GET: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@api_bp.route('/balanca/pesagem', methods=['POST'])
def receber_pesagem_balanca():
    """
    Endpoint para receber dados de pesagem de balanças digitais.
    
    Formato esperado:
    {
        "balanca_id": "ID_BALANCA",
        "animal_id": "ID_ANIMAL",
        "peso": PESO_KG,
        "bat": BATERIA (opcional),
        "tkn": "TOKEN_API"
    }
    
    Exemplo de chamada:
    POST /api/balanca/pesagem
    {
        "balanca_id": "BALANCA001",
        "animal_id": "BRINCO123",
        "peso": 450.5,
        "bat": 95.5,
        "tkn": "token-secreto-api"
    }
    """
    try:
        # Obter dados da requisição
        data = request.get_json() or {}
        
        # Validação básica dos campos obrigatórios
        for campo in ['balanca_id', 'animal_id', 'peso', 'tkn']:
            if campo not in data:
                return jsonify({"erro": f"Campo obrigatório ausente: {campo}"}), 400
        
        # Verificar autenticação
        propriedade = verificar_token(data['tkn'])
        if not propriedade:
            return jsonify({"erro": "Token de API inválido"}), 401
        
        # Buscar a balança pelo ID
        balanca = BalancaDigital.query.filter_by(codigo=data['balanca_id']).first()
        if not balanca:
            return jsonify({"erro": f"Balança não encontrada: {data['balanca_id']}"}), 404
        
        # Buscar o animal pelo código
        animal = Animal.query.filter_by(codigo=data['animal_id']).first()
        if not animal:
            return jsonify({"erro": f"Animal não encontrado: {data['animal_id']}"}), 404
        
        # Atualizar dados da balança
        balanca.ultimo_contato = datetime.now()
        
        # Atualizar bateria, se fornecida
        if 'bat' in data:
            balanca.bateria = data['bat']
        
        # Registrar pesagem
        pesagem = RegistroPeso(
            animal_id=animal.id,
            balanca_id=balanca.id,
            peso=data['peso'],
            data_pesagem=datetime.now(),
            metodo='automatica',
            observacao=f"Pesagem automática via balança {balanca.nome}"
        )
        
        # Atualizar peso atual do animal
        animal.peso_atual = data['peso']
        
        db.session.add(pesagem)
        db.session.commit()
        
        logger.info(f"Pesagem recebida via API para animal {animal.codigo}: {data['peso']} kg")
        
        return jsonify({"status": "sucesso", "animal": animal.codigo, "peso": data['peso']})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar pesagem da balança: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@api_bp.route('/balanca/pesagem/get', methods=['GET'])
def receber_pesagem_balanca_get():
    """
    Endpoint para receber dados de pesagem via GET (mais simples para dispositivos IoT).
    
    Parâmetros de URL:
    - balanca_id: ID da balança
    - animal_id: ID do animal (código)
    - peso: Peso em kg
    - bat: Bateria (opcional)
    - tkn: Token de API
    
    Exemplo:
    GET /api/balanca/pesagem/get?balanca_id=BALANCA001&animal_id=BOV123&peso=450.5&bat=95.5&tkn=token-secreto-api
    """
    try:
        # Obter dados da requisição
        balanca_id = request.args.get('balanca_id')
        animal_id = request.args.get('animal_id')
        peso = request.args.get('peso')
        bateria = request.args.get('bat')
        token = request.args.get('tkn')
        
        # Validação básica dos campos obrigatórios
        if not all([balanca_id, animal_id, peso, token]):
            return jsonify({"erro": "Parâmetros obrigatórios ausentes"}), 400
        
        # Converter valores
        try:
            peso = float(peso)
            bateria = float(bateria) if bateria is not None else None
        except ValueError:
            return jsonify({"erro": "Valores inválidos para peso/bateria"}), 400
        
        # Verificar autenticação
        propriedade = verificar_token(token)
        if not propriedade:
            return jsonify({"erro": "Token de API inválido"}), 401
        
        # Buscar a balança pelo ID
        balanca = BalancaDigital.query.filter_by(codigo=balanca_id).first()
        if not balanca:
            return jsonify({"erro": f"Balança não encontrada: {balanca_id}"}), 404
        
        # Buscar o animal pelo código
        animal = Animal.query.filter_by(codigo=animal_id).first()
        if not animal:
            return jsonify({"erro": f"Animal não encontrado: {animal_id}"}), 404
        
        # Atualizar dados da balança
        balanca.ultimo_contato = datetime.now()
        
        # Atualizar bateria, se fornecida
        if bateria is not None:
            balanca.bateria = bateria
        
        # Registrar pesagem
        pesagem = RegistroPeso(
            animal_id=animal.id,
            balanca_id=balanca.id,
            peso=peso,
            data_pesagem=datetime.now(),
            metodo='automatica',
            observacao=f"Pesagem automática via balança {balanca.nome}"
        )
        
        # Atualizar peso atual do animal
        animal.peso_atual = peso
        
        db.session.add(pesagem)
        db.session.commit()
        
        logger.info(f"Pesagem recebida via API GET para animal {animal.codigo}: {peso} kg")
        
        return jsonify({"status": "sucesso", "animal": animal.codigo, "peso": peso})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar pesagem da balança via GET: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@api_bp.route('/estacao/leitura', methods=['POST', 'GET'])
def receber_leitura_estacao():
    """
    Endpoint para receber dados de leituras de estações meteorológicas.
    Aceita requisições tanto POST (JSON) quanto GET (parâmetros de URL).
    
    Formato esperado POST:
    {
        "estacao_id": "ID_ESTACAO",
        "temp": TEMPERATURA,
        "umid": UMIDADE,
        "press": PRESSAO,
        "precip": PRECIPITACAO,
        "vento": VELOCIDADE_VENTO,
        "dir_vento": DIRECAO_VENTO,
        "bat": BATERIA,
        "tkn": "TOKEN_API"
    }
    
    Parâmetros de URL GET:
    - estacao_id: ID da estação
    - temp: Temperatura em °C
    - umid: Umidade relativa em %
    - press: Pressão atmosférica em hPa
    - precip: Precipitação em mm
    - vento: Velocidade do vento em km/h
    - dir_vento: Direção do vento em graus (0-360)
    - bat: Bateria em %
    - tkn: Token de API
    """
    try:
        # Determinar o método de requisição
        if request.method == 'POST':
            data = request.get_json() or {}
            estacao_id = data.get('estacao_id')
            temperatura = data.get('temp')
            umidade = data.get('umid')
            pressao = data.get('press')
            precipitacao = data.get('precip')
            velocidade_vento = data.get('vento')
            direcao_vento = data.get('dir_vento')
            bateria = data.get('bat')
            token = data.get('tkn')
        else: # GET
            estacao_id = request.args.get('estacao_id')
            temperatura = request.args.get('temp')
            umidade = request.args.get('umid')
            pressao = request.args.get('press')
            precipitacao = request.args.get('precip')
            velocidade_vento = request.args.get('vento')
            direcao_vento = request.args.get('dir_vento')
            bateria = request.args.get('bat')
            token = request.args.get('tkn')
        
        # Validação básica dos campos obrigatórios
        if not all([estacao_id, token]):
            return jsonify({"erro": "Parâmetros obrigatórios ausentes"}), 400
        
        # Converter valores, caso não sejam None
        try:
            temperatura = float(temperatura) if temperatura is not None else None
            umidade = float(umidade) if umidade is not None else None
            pressao = float(pressao) if pressao is not None else None
            precipitacao = float(precipitacao) if precipitacao is not None else None
            velocidade_vento = float(velocidade_vento) if velocidade_vento is not None else None
            direcao_vento = float(direcao_vento) if direcao_vento is not None else None
            bateria = float(bateria) if bateria is not None else None
        except ValueError:
            return jsonify({"erro": "Valores inválidos para os parâmetros"}), 400
        
        # Verificar autenticação
        propriedade = verificar_token(token)
        if not propriedade:
            return jsonify({"erro": "Token de API inválido"}), 401
        
        # Buscar a estação pelo código
        estacao = EstacaoMeteorologica.query.filter_by(codigo=estacao_id).first()
        if not estacao:
            return jsonify({"erro": f"Estação não encontrada: {estacao_id}"}), 404
        
        # Atualizar dados da estação
        estacao.ultimo_contato = datetime.now()
        
        # Atualizar bateria, se fornecida
        if bateria is not None:
            estacao.bateria = bateria
        
        # Registrar leitura
        leitura = LeituraMeteorologica(
            estacao_id=estacao.id,
            data_hora=datetime.now(),
            temperatura=temperatura,
            umidade=umidade,
            pressao=pressao,
            precipitacao=precipitacao,
            velocidade_vento=velocidade_vento,
            direcao_vento=direcao_vento,
            bateria=bateria
        )
        
        db.session.add(leitura)
        db.session.commit()
        
        logger.info(f"Leitura recebida via API para estação {estacao.codigo}")
        
        return jsonify({
            "status": "sucesso", 
            "estacao": estacao.codigo,
            "timestamp": leitura.data_hora.isoformat()
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar leitura da estação: {str(e)}")
        return jsonify({"erro": str(e)}), 500

# Para cadastrar como blueprints na aplicação
def init_app(app):
    app.register_blueprint(api_bp)
    logger.info("API de dispositivos LoRa e balanças registrada")