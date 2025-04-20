from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import uuid
import json

@login_manager.user_loader
def load_user(id):
    return Usuario.query.get(int(id))

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Propriedade(db.Model):
    __tablename__ = 'propriedades'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    inscricao_estadual = db.Column(db.String(20), unique=True)
    cpf_cnpj = db.Column(db.String(20), unique=True)
    endereco = db.Column(db.String(200))
    municipio = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    area_total = db.Column(db.Float) # em hectares
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Configurações do mapa
    tipo_mapa = db.Column(db.String(20), default='openstreetmap') # openstreetmap ou google
    google_maps_key = db.Column(db.String(100))
    
    # Token de API para integração com servidor LoRa
    api_token = db.Column(db.String(100))
    
    # Relacionamentos
    areas = db.relationship('Area', backref='propriedade', lazy=True)
    animais = db.relationship('Animal', backref='propriedade', lazy=True)
    atividades = db.relationship('Atividade', backref='propriedade', lazy=True)

class Area(db.Model):
    __tablename__ = 'areas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50)) # pasto, curral, mata, etc
    tamanho = db.Column(db.Float) # em hectares
    coordenadas = db.Column(db.Text) # GeoJSON poligono
    cor = db.Column(db.String(7), default="#3388ff") # cor no mapa
    propriedade_id = db.Column(db.Integer, db.ForeignKey('propriedades.id'), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_coordenadas(self, polygon_coords):
        """Recebe uma lista de coordenadas [lng, lat] e salva como GeoJSON"""
        geojson = {
            "type": "Polygon",
            "coordinates": [polygon_coords]
        }
        self.coordenadas = json.dumps(geojson)
    
    def get_coordenadas(self):
        """Retorna o polígono como GeoJSON"""
        if self.coordenadas:
            return json.loads(self.coordenadas)
        return None

class Raca(db.Model):
    __tablename__ = 'racas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    especie = db.Column(db.String(50), nullable=False) # bovino, ovino, caprino, etc
    descricao = db.Column(db.Text)
    
    # Relacionamento
    animais = db.relationship('Animal', backref='raca', lazy=True)

class Animal(db.Model):
    __tablename__ = 'animais'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100))
    sexo = db.Column(db.String(1)) # M ou F
    data_nascimento = db.Column(db.Date)
    peso_atual = db.Column(db.Float) # em kg
    status = db.Column(db.String(20), default='Ativo') # Ativo, Vendido, Morto
    
    # Personalização
    cor = db.Column(db.String(7), default="#000000") # cor para exibição no mapa (formato hex #RRGGBB)
    
    # Dispositivo LoRa
    id_dispositivo = db.Column(db.String(36), unique=True)
    ultima_latitude = db.Column(db.Float)
    ultima_longitude = db.Column(db.Float)
    ultima_atualizacao = db.Column(db.DateTime)
    bateria = db.Column(db.Float) # percentual de bateria
    
    # Relacionamentos
    propriedade_id = db.Column(db.Integer, db.ForeignKey('propriedades.id'), nullable=False)
    raca_id = db.Column(db.Integer, db.ForeignKey('racas.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'))
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'))
    mae_id = db.Column(db.Integer, db.ForeignKey('animais.id'))
    pai_id = db.Column(db.Integer, db.ForeignKey('animais.id'))
    
    # Relacionamentos bidirecionais
    area = db.relationship('Area', foreign_keys=[area_id])
    lote = db.relationship('Lote', back_populates='animais')
    mae = db.relationship('Animal', remote_side=[id], foreign_keys=[mae_id])
    pai = db.relationship('Animal', remote_side=[id], foreign_keys=[pai_id])
    
    # Relacionamentos de uma para muitos
    registros_peso = db.relationship('RegistroPeso', backref='animal', lazy=True)
    registros_sanitarios = db.relationship('RegistroSanitario', backref='animal', lazy=True)
    
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    def gerar_dispositivo_lora(self):
        """Gera um ID para o dispositivo LoRa"""
        self.id_dispositivo = str(uuid.uuid4())
        return self.id_dispositivo

class Lote(db.Model):
    __tablename__ = 'lotes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.String(50)) # engorda, cria, recria, etc
    data_formacao = db.Column(db.Date, default=datetime.utcnow)
    
    # Relacionamentos
    animais = db.relationship('Animal', back_populates='lote')

class BalancaDigital(db.Model):
    __tablename__ = 'balancas_digitais'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100))
    fabricante = db.Column(db.String(100))
    localizacao = db.Column(db.String(200))
    data_instalacao = db.Column(db.Date)
    status = db.Column(db.String(20), default='Ativo') # Ativo, Inativo, Manutenção
    
    # Conexão LoRa ou outras configurações de conectividade
    device_id = db.Column(db.String(36), unique=True)
    bateria = db.Column(db.Float) # percentual de bateria
    ultimo_contato = db.Column(db.DateTime)
    
    # Token de autenticação para API
    token_api = db.Column(db.String(100))
    
    # Precisão em kg (exemplo: 0.5, 1, 5)
    precisao = db.Column(db.Float, default=0.5)
    
    # Capacidade máxima em kg
    capacidade_max = db.Column(db.Float)
    
    # Relacionamentos
    propriedade_id = db.Column(db.Integer, db.ForeignKey('propriedades.id'), nullable=False)
    propriedade = db.relationship('Propriedade', backref='balancas')
    
    # Pesagens realizadas por esta balança
    pesagens = db.relationship('RegistroPeso', backref='balanca', lazy=True)
    
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def gerar_token_api(self):
        """Gera um token de API para a balança"""
        self.token_api = str(uuid.uuid4())
        return self.token_api

class RegistroPeso(db.Model):
    __tablename__ = 'registros_peso'
    
    id = db.Column(db.Integer, primary_key=True)
    peso = db.Column(db.Float, nullable=False) # em kg
    data_pesagem = db.Column(db.DateTime, default=datetime.utcnow)
    observacao = db.Column(db.Text)
    
    # Método de pesagem: manual ou automatica
    metodo = db.Column(db.String(20), default='manual')
    
    # Relacionamentos
    animal_id = db.Column(db.Integer, db.ForeignKey('animais.id'), nullable=False)
    balanca_id = db.Column(db.Integer, db.ForeignKey('balancas_digitais.id'))

class RegistroSanitario(db.Model):
    __tablename__ = 'registros_sanitarios'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False) # vacinação, vermifugação, etc
    produto = db.Column(db.String(100))
    dose = db.Column(db.Float)
    unidade_dose = db.Column(db.String(10)) # ml, mg, etc
    data_aplicacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_proxima = db.Column(db.Date)
    responsavel = db.Column(db.String(100))
    observacao = db.Column(db.Text)
    
    # Relacionamento
    animal_id = db.Column(db.Integer, db.ForeignKey('animais.id'), nullable=False)

class Atividade(db.Model):
    __tablename__ = 'atividades'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False) # plantio, colheita, adubação, etc
    descricao = db.Column(db.Text, nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Planejada') # Planejada, Em Andamento, Concluída, Cancelada
    responsavel = db.Column(db.String(100))
    custo = db.Column(db.Float)
    observacao = db.Column(db.Text)
    
    # Relacionamentos
    propriedade_id = db.Column(db.Integer, db.ForeignKey('propriedades.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'))
    
    # Relacionamento bidirecional
    area = db.relationship('Area', backref='atividades')

class DispositivoLora(db.Model):
    __tablename__ = 'dispositivos_lora'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(36), unique=True, nullable=False)
    tipo = db.Column(db.String(50)) # brinco, colar, etc
    data_ativacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_contato = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Ativo') # Ativo, Inativo, Manutenção
    bateria = db.Column(db.Float) # percentual de bateria
    firmware = db.Column(db.String(20))
    
    # Relacionamento
    animal_id = db.Column(db.Integer, db.ForeignKey('animais.id'))
    animal = db.relationship('Animal', foreign_keys=[animal_id])

class HistoricoLocalizacao(db.Model):
    __tablename__ = 'historico_localizacao'
    
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    bateria = db.Column(db.Float) # percentual de bateria
    
    # Relacionamentos
    animal_id = db.Column(db.Integer, db.ForeignKey('animais.id'), nullable=False)
    device_id = db.Column(db.String(36), nullable=False)

class EstacaoMeteorologica(db.Model):
    __tablename__ = 'estacoes_meteorologicas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    modelo = db.Column(db.String(50))
    fabricante = db.Column(db.String(100))
    data_instalacao = db.Column(db.Date)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Float) # em metros
    status = db.Column(db.String(20), default='Ativo') # Ativo, Inativo, Manutenção
    intervalo_leitura = db.Column(db.Integer, default=15) # em minutos
    
    # Sensores disponíveis (flags)
    sensor_temperatura = db.Column(db.Boolean, default=True)
    sensor_umidade = db.Column(db.Boolean, default=True)
    sensor_pressao = db.Column(db.Boolean, default=True)
    sensor_vento = db.Column(db.Boolean, default=True)
    sensor_chuva = db.Column(db.Boolean, default=True)
    sensor_radiacao = db.Column(db.Boolean, default=False)
    sensor_solo = db.Column(db.Boolean, default=False)
    
    # Conexão LoRa
    device_id = db.Column(db.String(36), unique=True)
    firmware = db.Column(db.String(20))
    bateria = db.Column(db.Float) # percentual de bateria
    ultimo_contato = db.Column(db.DateTime)
    
    # Relacionamentos
    propriedade_id = db.Column(db.Integer, db.ForeignKey('propriedades.id'), nullable=False)
    propriedade = db.relationship('Propriedade', backref='estacoes_meteorologicas')
    
    leituras = db.relationship('LeituraMeteorologica', backref='estacao', lazy=True, cascade="all, delete-orphan")
    alertas = db.relationship('AlertaMeteorologico', backref='estacao', lazy=True, cascade="all, delete-orphan")
    
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    def gerar_device_id(self):
        """Gera um ID para o dispositivo LoRa"""
        self.device_id = str(uuid.uuid4())
        return self.device_id

class LeituraMeteorologica(db.Model):
    __tablename__ = 'leituras_meteorologicas'

    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Dados meteorológicos
    temperatura = db.Column(db.Float) # em °C
    umidade = db.Column(db.Float) # em %
    pressao = db.Column(db.Float) # em hPa
    velocidade_vento = db.Column(db.Float) # em km/h
    direcao_vento = db.Column(db.Float) # em graus (0-360)
    precipitacao = db.Column(db.Float) # em mm
    radiacao_solar = db.Column(db.Float) # em W/m²
    
    # Dados do solo (opcionais)
    umidade_solo = db.Column(db.Float) # em %
    temperatura_solo = db.Column(db.Float) # em °C
    
    # Dados do dispositivo
    bateria = db.Column(db.Float) # percentual de bateria
    sinal_lora = db.Column(db.Float) # intensidade do sinal (dBm)
    
    estacao_id = db.Column(db.Integer, db.ForeignKey('estacoes_meteorologicas.id'), nullable=False)

class AlertaMeteorologico(db.Model):
    __tablename__ = 'alertas_meteorologicos'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False) # Chuva, Seca, Geada, Tempestade, etc
    descricao = db.Column(db.Text, nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    nivel = db.Column(db.String(20), nullable=False) # Informativo, Atenção, Alerta, Emergência
    status = db.Column(db.String(20), default='Ativo') # Ativo, Reconhecido, Finalizado
    
    # Dados da condição que gerou o alerta
    valor_medido = db.Column(db.Float)
    valor_limite = db.Column(db.Float)
    unidade = db.Column(db.String(10)) # mm, °C, km/h, etc
    
    estacao_id = db.Column(db.Integer, db.ForeignKey('estacoes_meteorologicas.id'), nullable=False)
    
    # Opcional - pessoa que reconheceu o alerta
    reconhecido_por = db.Column(db.String(100))
    data_reconhecimento = db.Column(db.DateTime)
