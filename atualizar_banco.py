"""
Script para atualizar o esquema do banco de dados.

Este script adiciona campos necessários para as novas funcionalidades
da API LoRa e Balanças digitais.
"""

import logging
from app import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def adicionar_campos_registro_peso():
    """Adiciona os campos metodo e balanca_id à tabela registros_peso"""
    with app.app_context():
        # Verificar se a coluna metodo já existe
        metodo_existe = False
        balanca_id_existe = False
        
        # Usar conexões separadas para cada consulta para evitar problemas de transação
        try:
            # Tentar verificar se as colunas existem usando metadata
            conn = db.engine.connect()
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='registros_peso' AND column_name='metodo'"))
            metodo_existe = result.rowcount > 0
            conn.close()
            
            conn = db.engine.connect()
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='registros_peso' AND column_name='balanca_id'"))
            balanca_id_existe = result.rowcount > 0
            conn.close()
            
            # Adicionar coluna metodo se não existir
            if not metodo_existe:
                logger.info("Adicionando coluna 'metodo' à tabela registros_peso")
                conn = db.engine.connect()
                conn.execute(text("ALTER TABLE registros_peso ADD COLUMN metodo VARCHAR(20) DEFAULT 'manual'"))
                conn.commit()
                conn.close()
            else:
                logger.info("Coluna 'metodo' já existe na tabela registros_peso")
            
            # Adicionar coluna balanca_id se não existir
            if not balanca_id_existe:
                logger.info("Adicionando coluna 'balanca_id' à tabela registros_peso")
                conn = db.engine.connect()
                conn.execute(text("ALTER TABLE registros_peso ADD COLUMN balanca_id INTEGER"))
                conn.commit()
                conn.close()
                
                conn = db.engine.connect()
                conn.execute(text("ALTER TABLE registros_peso ADD CONSTRAINT fk_balanca_id FOREIGN KEY (balanca_id) REFERENCES balancas_digitais(id)"))
                conn.commit()
                conn.close()
            else:
                logger.info("Coluna 'balanca_id' já existe na tabela registros_peso")
            
            logger.info("Tabela registros_peso atualizada com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar tabela registros_peso: {str(e)}")
            return False

def verificar_tabela_balancas():
    """Verifica se a tabela balancas_digitais existe e cria se não existir"""
    with app.app_context():
        try:
            # Verificar se a tabela existe usando information_schema
            conn = db.engine.connect()
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'balancas_digitais')"
            ))
            tabela_existe = result.scalar()
            conn.close()
            
            if not tabela_existe:
                logger.info("Criando tabela 'balancas_digitais'")
                conn = db.engine.connect()
                conn.execute(text("""
                CREATE TABLE balancas_digitais (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(50) NOT NULL UNIQUE,
                    nome VARCHAR(100) NOT NULL,
                    modelo VARCHAR(100),
                    fabricante VARCHAR(100),
                    localizacao VARCHAR(200),
                    data_instalacao DATE,
                    status VARCHAR(20) DEFAULT 'Ativo',
                    device_id VARCHAR(36) UNIQUE,
                    bateria FLOAT,
                    ultimo_contato TIMESTAMP,
                    token_api VARCHAR(100),
                    precisao FLOAT DEFAULT 0.5,
                    capacidade_max FLOAT,
                    propriedade_id INTEGER NOT NULL REFERENCES propriedades(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """))
                conn.commit()
                conn.close()
                logger.info("Tabela balancas_digitais criada com sucesso!")
            else:
                logger.info("Tabela balancas_digitais já existe!")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar/criar tabela balancas_digitais: {str(e)}")
            return False

if __name__ == "__main__":
    logger.info("Iniciando migração do banco de dados")
    
    # Verificar e criar tabela de balanças
    if verificar_tabela_balancas():
        # Adicionar campos à tabela registros_peso
        adicionar_campos_registro_peso()
    
    logger.info("Migração concluída")