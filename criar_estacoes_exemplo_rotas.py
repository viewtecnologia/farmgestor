"""
Rotas para criação de dados de exemplo.

Este módulo contém rotas para criar dados de demonstração,
como estações meteorológicas e balanças digitais.
"""

import logging
from datetime import datetime, timedelta
import uuid
import random
import requests
import flask
from flask import Blueprint, jsonify, request, redirect, url_for, flash
from app import app, db
from models import EstacaoMeteorologica, LeituraMeteorologica, BalancaDigital, Propriedade

# Configuração de logging
logger = logging.getLogger(__name__)

# Criação do blueprint
exemplo_bp = Blueprint('exemplo', __name__, url_prefix='/exemplo')

@exemplo_bp.route('/criar-estacao')
def criar_estacao_exemplo():
    """
    Cria uma estação meteorológica de exemplo para demonstração
    """
    try:
        # Verificar se já existe uma propriedade
        propriedade = Propriedade.query.first()
        if not propriedade:
            return jsonify({"erro": "Nenhuma propriedade cadastrada. Cadastre uma propriedade primeiro."}), 400
        
        # Dados da estação
        estacao = EstacaoMeteorologica(
            nome="Estação Central",
            codigo="EST001",
            descricao="Estação meteorológica central para demonstração",
            modelo="WeatherMaster 3000",
            fabricante="TechSense",
            data_instalacao=datetime.now().date(),
            latitude=propriedade.latitude + random.uniform(-0.01, 0.01) if propriedade.latitude else -23.5505,
            longitude=propriedade.longitude + random.uniform(-0.01, 0.01) if propriedade.longitude else -46.6333,
            altitude=800.0,
            status="Ativo",
            intervalo_leitura=15,
            sensor_temperatura=True,
            sensor_umidade=True,
            sensor_pressao=True,
            sensor_vento=True,
            sensor_chuva=True,
            sensor_radiacao=True,
            sensor_solo=True,
            propriedade_id=propriedade.id,
            bateria=95.0
        )
        
        # Gerar ID do dispositivo
        estacao.gerar_device_id()
        
        db.session.add(estacao)
        db.session.commit()
        
        # Gerar algumas leituras iniciais
        for i in range(24):  # Últimas 24 horas, com intervalo de 1 hora
            hora = datetime.now() - timedelta(hours=24-i)
            
            # Variação diurna com pico às 14h
            hora_do_dia = hora.hour
            temp_base = 22.0  # temperatura base
            temp_variacao = 8.0  # variação máxima
            
            # Fórmula para simular variação diurna de temperatura
            # com pico às 14h (quando hora_do_dia=14, o cosseno é mínimo)
            temperatura = temp_base + temp_variacao * (1 - abs(((hora_do_dia - 14) % 24) / 12 - 1))
            
            # Umidade inversamente proporcional à temperatura (mais ou menos)
            umidade = 100 - (temperatura - temp_base) * 5 + random.uniform(-5, 5)
            umidade = max(30, min(95, umidade))  # limitar entre 30% e 95%
            
            # Dados mais aleatórios para os outros sensores
            leitura = LeituraMeteorologica(
                estacao_id=estacao.id,
                data_hora=hora,
                temperatura=temperatura + random.uniform(-0.5, 0.5),
                umidade=umidade,
                pressao=1013.0 + random.uniform(-5, 5),
                velocidade_vento=random.uniform(0, 15),
                direcao_vento=random.uniform(0, 360),
                precipitacao=random.uniform(0, 2.5) if random.random() > 0.7 else 0,
                radiacao_solar=random.uniform(0, 950) if hora_do_dia >= 6 and hora_do_dia <= 18 else random.uniform(0, 50),
                umidade_solo=65.0 + random.uniform(-10, 10),
                temperatura_solo=18.0 + random.uniform(-2, 2),
                bateria=95.0 - (i * 0.1),
                sinal_lora=-70.0 + random.uniform(-10, 5)
            )
            
            db.session.add(leitura)
        
        db.session.commit()
        
        logger.info(f"Estação meteorológica de exemplo criada: {estacao.nome}")
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Estação meteorológica de exemplo criada com sucesso",
            "estacao": {
                "id": estacao.id,
                "nome": estacao.nome,
                "codigo": estacao.codigo,
                "device_id": estacao.device_id
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar estação de exemplo: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@exemplo_bp.route('/criar-balanca')
def criar_balanca_exemplo():
    """
    Cria uma balança digital de exemplo para demonstração
    """
    try:
        # Verificar se já existe uma propriedade
        propriedade = Propriedade.query.first()
        if not propriedade:
            return jsonify({"erro": "Nenhuma propriedade cadastrada. Cadastre uma propriedade primeiro."}), 400
        
        # Dados da balança
        balanca = BalancaDigital(
            codigo="BAL001",
            nome="Balança Central",
            modelo="PesoExato 5000",
            fabricante="TechRural",
            localizacao="Curral principal",
            data_instalacao=datetime.now().date(),
            status="Ativo",
            bateria=98.5,
            ultimo_contato=datetime.now(),
            precisao=0.5,
            capacidade_max=2000.0,
            propriedade_id=propriedade.id
        )
        
        # Gerar token de API
        balanca.gerar_token_api()
        
        db.session.add(balanca)
        db.session.commit()
        
        logger.info(f"Balança digital de exemplo criada: {balanca.nome}")
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Balança digital de exemplo criada com sucesso",
            "balanca": {
                "id": balanca.id,
                "nome": balanca.nome,
                "codigo": balanca.codigo,
                "token_api": balanca.token_api
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar balança de exemplo: {str(e)}")
        return jsonify({"erro": str(e)}), 500

# Configuração das rotas
def init_app(app):
    app.register_blueprint(exemplo_bp)
    logger.info("Rotas de exemplo registradas")

# Registro das rotas
init_app(app)