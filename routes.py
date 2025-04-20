import os
import json
import logging
import random
import io
import re
import zipfile
from lxml import etree
from pykml import parser as kml_parser
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import pandas as pd
from io import BytesIO

from app import app, db
from models import (
    Usuario, Propriedade, Area, Raca, Animal, Lote, 
    RegistroPeso, RegistroSanitario, Atividade, 
    DispositivoLora, HistoricoLocalizacao,
    EstacaoMeteorologica, LeituraMeteorologica, AlertaMeteorologico
)
from lora_communication import LoRaManager, simulate_lora_data

# Configuração de logging

# Context processor para adicionar variáveis a todas as templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}
logger = logging.getLogger(__name__)

# Instância do gerenciador LoRa
lora_manager = LoRaManager()

# Funções auxiliares para processamento de KML/KMZ
def processar_kml(arquivo_kml):
    """
    Processa um arquivo KML e extrai coordenadas de polígonos
    
    Args:
        arquivo_kml: Objeto de arquivo KML
        
    Returns:
        list: Lista de coordenadas no formato [[lng, lat], ...]
    """
    try:
        # Analisar o arquivo KML
        root = kml_parser.parse(arquivo_kml).getroot()
        
        # Encontrar o primeiro polígono no arquivo KML
        # Procurar dentro do namespace correto
        namespace = '{http://www.opengis.net/kml/2.2}'
        polygon = root.findall('.//' + namespace + 'Polygon')
        
        if not polygon:
            return None
        
        # Obter as coordenadas do polígono (primeiro encontrado)
        coords_elem = polygon[0].findall('.//' + namespace + 'coordinates')
        
        if not coords_elem or not coords_elem[0].text:
            return None
        
        # Processar string de coordenadas
        coordenadas_str = coords_elem[0].text.strip()
        
        # Converter para lista de [lng, lat]
        resultado = []
        
        # KML usa formato lon,lat,alt com espaços ou quebras de linha entre pontos
        for ponto in re.split(r'\s+', coordenadas_str):
            if ponto.strip():
                partes = ponto.split(',')
                if len(partes) >= 2:
                    lon, lat = float(partes[0]), float(partes[1])
                    resultado.append([lon, lat])
        
        return resultado
    
    except Exception as e:
        logger.error(f"Erro ao processar arquivo KML: {str(e)}")
        raise
        
def processar_kmz(arquivo_kmz):
    """
    Processa um arquivo KMZ (arquivo ZIP contendo KML)
    
    Args:
        arquivo_kmz: Objeto de arquivo KMZ
        
    Returns:
        list: Lista de coordenadas no formato [[lng, lat], ...]
    """
    try:
        # Criar um arquivo ZIP em memória
        kmz_zip = zipfile.ZipFile(arquivo_kmz)
        
        # Encontrar o arquivo KML dentro do KMZ
        kml_file = None
        for item in kmz_zip.namelist():
            if item.lower().endswith('.kml'):
                kml_file = item
                break
        
        if not kml_file:
            return None
        
        # Extrair o arquivo KML
        with kmz_zip.open(kml_file) as kml_content:
            # Processar o arquivo KML extraído
            return processar_kml(kml_content)
    
    except Exception as e:
        logger.error(f"Erro ao processar arquivo KMZ: {str(e)}")
        raise

# Rota inicial
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        user = Usuario.query.filter_by(email=email).first()
        
        if user and user.check_password(senha):
            login_user(user)
            flash('Login efetuado com sucesso.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('index'))

# Dashboard principal
@app.route('/dashboard')
@login_required
def dashboard():
    # Estatísticas básicas
    total_animais = Animal.query.count()
    total_areas = Area.query.count()
    total_atividades = Atividade.query.count()
    
    # Animais por status
    animais_ativos = Animal.query.filter_by(status='Ativo').count()
    animais_vendidos = Animal.query.filter_by(status='Vendido').count()
    animais_mortos = Animal.query.filter_by(status='Morto').count()
    
    # Animais por sexo
    animais_machos = Animal.query.filter_by(sexo='M', status='Ativo').count()
    animais_femeas = Animal.query.filter_by(sexo='F', status='Ativo').count()
    
    # Animais com bateria baixa (dispositivos LoRa)
    animais_bateria_baixa = Animal.query.filter(
        Animal.id_dispositivo != None,
        Animal.bateria < 20
    ).count()
    
    # Atividades pendentes
    atividades_pendentes = Atividade.query.filter(
        Atividade.status.in_(['Planejada', 'Em Andamento'])
    ).order_by(Atividade.data_inicio).limit(5).all()
    
    # Simular novos dados dos dispositivos LoRa (em produção seria um processo separado)
    simulate_lora_data()
    
    # Peso médio por raça (para o novo gráfico simplificado)
    pesos_racas = db.session.query(
        Raca.nome.label('raca'),
        db.func.avg(Animal.peso_atual).label('peso_medio')
    ).join(Animal).filter(Animal.peso_atual != None).group_by(Raca.nome).all()
    
    racas_pesos = [(r.raca, round(r.peso_medio, 2)) for r in pesos_racas]
    
    # Animais por área (para o novo gráfico simplificado)
    animais_areas = db.session.query(
        Area.nome.label('area'),
        db.func.count(Animal.id).label('total')
    ).outerjoin(Animal, Area.id == Animal.area_id).group_by(Area.nome).all()
    
    areas_totais = [(a.area, a.total) for a in animais_areas]
    
    return render_template(
        'dashboard.html',
        total_animais=total_animais,
        total_areas=total_areas,
        total_atividades=total_atividades,
        animais_ativos=animais_ativos,
        animais_vendidos=animais_vendidos,
        animais_mortos=animais_mortos,
        animais_machos=animais_machos,
        animais_femeas=animais_femeas,
        animais_bateria_baixa=animais_bateria_baixa,
        atividades_pendentes=atividades_pendentes,
        racas_pesos=racas_pesos,
        areas_totais=areas_totais
    )

# Rotas para gerenciamento de animais
@app.route('/animais')
@login_required
def listar_animais():
    animais = Animal.query.all()
    racas = Raca.query.all()
    areas = Area.query.all()
    lotes = Lote.query.all()
    
    return render_template(
        'listar_animais.html',
        animais=animais,
        racas=racas,
        areas=areas,
        lotes=lotes
    )

@app.route('/animais/novo', methods=['GET', 'POST'])
@login_required
def cadastro_animal():
    if request.method == 'POST':
        try:
            codigo = request.form.get('codigo')
            nome = request.form.get('nome')
            sexo = request.form.get('sexo')
            data_nascimento = datetime.strptime(request.form.get('data_nascimento'), '%Y-%m-%d')
            peso = float(request.form.get('peso'))
            raca_id = int(request.form.get('raca_id'))
            area_id = int(request.form.get('area_id')) if request.form.get('area_id') else None
            lote_id = int(request.form.get('lote_id')) if request.form.get('lote_id') else None
            mae_id = int(request.form.get('mae_id')) if request.form.get('mae_id') else None
            pai_id = int(request.form.get('pai_id')) if request.form.get('pai_id') else None
            
            # Verifica se propriedade existe
            propriedade = Propriedade.query.first()
            if not propriedade:
                flash('Nenhuma propriedade cadastrada no sistema.', 'danger')
                return redirect(url_for('listar_animais'))
            
            # Obter a cor escolhida pelo usuário
            cor = request.form.get('cor', '#000000')
            
            animal = Animal(
                codigo=codigo,
                nome=nome,
                sexo=sexo,
                data_nascimento=data_nascimento,
                peso_atual=peso,
                cor=cor,
                raca_id=raca_id,
                propriedade_id=propriedade.id,
                area_id=area_id,
                lote_id=lote_id,
                mae_id=mae_id,
                pai_id=pai_id
            )
            
            # Verifica se deve gerar dispositivo LoRa
            if request.form.get('gerar_dispositivo') == 'sim':
                device_id = animal.gerar_dispositivo_lora()
                
                # Cria registro do dispositivo
                dispositivo = DispositivoLora(
                    device_id=device_id,
                    tipo='Brinco',
                    animal_id=None  # Será atualizado após salvar o animal
                )
                db.session.add(dispositivo)
            
            # Registrar o peso inicial
            registro_peso = RegistroPeso(
                peso=peso,
                animal_id=None,  # Será atualizado após salvar o animal
                observacao="Peso inicial no cadastro"
            )
            
            db.session.add(animal)
            db.session.flush()  # Para obter o ID do animal
            
            # Atualiza o animal_id no registro de peso
            registro_peso.animal_id = animal.id
            db.session.add(registro_peso)
            
            # Atualiza o animal_id no dispositivo LoRa, se aplicável
            if request.form.get('gerar_dispositivo') == 'sim':
                dispositivo.animal_id = animal.id
            
            db.session.commit()
            flash('Animal cadastrado com sucesso.', 'success')
            return redirect(url_for('listar_animais'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar animal: {str(e)}', 'danger')
            logger.error(f"Erro ao cadastrar animal: {str(e)}")
    
    racas = Raca.query.all()
    areas = Area.query.all()
    lotes = Lote.query.all()
    animais_femeas = Animal.query.filter_by(sexo='F').all()
    animais_machos = Animal.query.filter_by(sexo='M').all()
    
    return render_template(
        'cadastro_animal.html',
        racas=racas,
        areas=areas,
        lotes=lotes,
        animais_femeas=animais_femeas,
        animais_machos=animais_machos
    )

@app.route('/animais/<int:id>')
@login_required
def detalhes_animal(id):
    animal = Animal.query.get_or_404(id)
    registros_peso = RegistroPeso.query.filter_by(animal_id=id).order_by(RegistroPeso.data_pesagem.desc()).all()
    registros_sanitarios = RegistroSanitario.query.filter_by(animal_id=id).order_by(RegistroSanitario.data_aplicacao.desc()).all()
    historico_localizacao = HistoricoLocalizacao.query.filter_by(animal_id=id).order_by(HistoricoLocalizacao.data_hora.desc()).limit(100).all()
    
    # Adicionar data atual para comparações no template
    now = datetime.now()
    
    return render_template(
        'detalhes_animal.html',
        animal=animal,
        registros_peso=registros_peso,
        registros_sanitarios=registros_sanitarios,
        historico_localizacao=historico_localizacao,
        now=now
    )

@app.route('/animais/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_animal(id):
    animal = Animal.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            animal.codigo = request.form.get('codigo')
            animal.nome = request.form.get('nome')
            animal.sexo = request.form.get('sexo')
            animal.data_nascimento = datetime.strptime(request.form.get('data_nascimento'), '%Y-%m-%d')
            animal.peso_atual = float(request.form.get('peso'))
            animal.status = request.form.get('status')
            animal.cor = request.form.get('cor', '#000000')
            animal.raca_id = int(request.form.get('raca_id'))
            
            # Campos opcionais
            animal.area_id = int(request.form.get('area_id')) if request.form.get('area_id') else None
            animal.lote_id = int(request.form.get('lote_id')) if request.form.get('lote_id') else None
            animal.mae_id = int(request.form.get('mae_id')) if request.form.get('mae_id') else None
            animal.pai_id = int(request.form.get('pai_id')) if request.form.get('pai_id') else None
            
            # Verificar se deve gerar ou remover dispositivo LoRa
            if not animal.id_dispositivo and request.form.get('gerar_dispositivo') == 'sim':
                # Gerar novo dispositivo LoRa
                device_id = animal.gerar_dispositivo_lora()
                
                # Criar registro do dispositivo
                dispositivo = DispositivoLora(
                    device_id=device_id,
                    tipo='Brinco',
                    animal_id=animal.id
                )
                db.session.add(dispositivo)
            
            elif animal.id_dispositivo and request.form.get('remover_dispositivo') == 'sim':
                # Remover dispositivo LoRa
                dispositivo = DispositivoLora.query.filter_by(device_id=animal.id_dispositivo).first()
                if dispositivo:
                    db.session.delete(dispositivo)
                animal.id_dispositivo = None
                animal.ultima_latitude = None
                animal.ultima_longitude = None
                animal.ultima_atualizacao = None
                animal.bateria = None
            
            db.session.commit()
            flash('Animal atualizado com sucesso!', 'success')
            return redirect(url_for('detalhes_animal', id=animal.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar animal: {str(e)}', 'danger')
            logger.error(f"Erro ao atualizar animal: {str(e)}")
    
    # Buscar dados para popular o formulário
    racas = Raca.query.all()
    areas = Area.query.all()
    lotes = Lote.query.all()
    
    # Buscar animais para genealogia, excluindo o próprio animal
    animais_femeas = Animal.query.filter(Animal.sexo == 'F', Animal.id != animal.id).all()
    animais_machos = Animal.query.filter(Animal.sexo == 'M', Animal.id != animal.id).all()
    
    return render_template(
        'editar_animal.html',
        animal=animal,
        racas=racas,
        areas=areas,
        lotes=lotes,
        animais_femeas=animais_femeas,
        animais_machos=animais_machos
    )

@app.route('/animais/<int:id>/registrar-peso', methods=['POST'])
@login_required
def registrar_peso(id):
    try:
        animal = Animal.query.get_or_404(id)
        
        peso = float(request.form.get('peso'))
        observacao = request.form.get('observacao', '')
        
        registro = RegistroPeso(
            peso=peso,
            animal_id=id,
            observacao=observacao
        )
        
        # Atualiza o peso atual do animal
        animal.peso_atual = peso
        
        db.session.add(registro)
        db.session.commit()
        
        flash('Peso registrado com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar peso: {str(e)}', 'danger')
        logger.error(f"Erro ao registrar peso: {str(e)}")
    
    return redirect(url_for('detalhes_animal', id=id))

@app.route('/animais/<int:id>/registrar-sanitario', methods=['POST'])
@login_required
def registrar_sanitario(id):
    try:
        tipo = request.form.get('tipo')
        produto = request.form.get('produto')
        dose = float(request.form.get('dose'))
        unidade_dose = request.form.get('unidade_dose')
        responsavel = request.form.get('responsavel')
        observacao = request.form.get('observacao', '')
        
        # Verificar data da próxima aplicação
        data_proxima = request.form.get('data_proxima')
        if data_proxima:
            data_proxima = datetime.strptime(data_proxima, '%Y-%m-%d')
        else:
            data_proxima = None
        
        registro = RegistroSanitario(
            tipo=tipo,
            produto=produto,
            dose=dose,
            unidade_dose=unidade_dose,
            responsavel=responsavel,
            data_proxima=data_proxima,
            observacao=observacao,
            animal_id=id
        )
        
        db.session.add(registro)
        db.session.commit()
        
        flash('Registro sanitário adicionado com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar sanitário: {str(e)}', 'danger')
        logger.error(f"Erro ao registrar sanitário: {str(e)}")
    
    return redirect(url_for('detalhes_animal', id=id))

@app.route('/animais/<int:id>/solicitar-localizacao', methods=['POST'])
@login_required
def solicitar_localizacao(id):
    animal = Animal.query.get_or_404(id)
    
    if not animal.id_dispositivo:
        flash('Este animal não possui dispositivo LoRa.', 'warning')
        return redirect(url_for('detalhes_animal', id=id))
    
    # Conectar ao gateway LoRa (se necessário)
    if not lora_manager.gateway_connected:
        lora_manager.connect_to_gateway()
    
    # Solicitar localização
    localizacao = lora_manager.request_location(animal.id_dispositivo)
    
    if localizacao:
        # Atualizar animal com novos dados
        animal.ultima_latitude = localizacao['latitude']
        animal.ultima_longitude = localizacao['longitude']
        animal.bateria = localizacao['battery']
        animal.ultima_atualizacao = datetime.now()
        
        # Registrar no histórico
        historico = HistoricoLocalizacao(
            animal_id=id,
            device_id=animal.id_dispositivo,
            latitude=localizacao['latitude'],
            longitude=localizacao['longitude'],
            bateria=localizacao['battery']
        )
        
        db.session.add(historico)
        db.session.commit()
        
        flash('Localização atualizada com sucesso.', 'success')
    else:
        flash('Não foi possível obter a localização atual.', 'danger')
    
    return redirect(url_for('detalhes_animal', id=id))

# Rotas para mapa da propriedade
@app.route('/mapa')
@login_required
def mapa_propriedade():
    areas = Area.query.all()
    animais = Animal.query.filter(
        Animal.ultima_latitude != None,
        Animal.ultima_longitude != None,
        Animal.status == 'Ativo'
    ).all()
    
    propriedade = Propriedade.query.first()
    
    # Verificar configurações do mapa
    tipo_mapa = 'openstreetmap'  # Padrão
    google_maps_key = ''
    
    if propriedade:
        tipo_mapa = propriedade.tipo_mapa or 'openstreetmap'
        google_maps_key = propriedade.google_maps_key or ''
    
    return render_template(
        'mapa_propriedade.html',
        areas=areas,
        animais=animais,
        propriedade=propriedade,
        tipo_mapa=tipo_mapa,
        google_maps_key=google_maps_key
    )

@app.route('/api/mapa/areas')
@login_required
def api_mapa_areas():
    areas = Area.query.all()
    features = []
    
    for area in areas:
        if area.coordenadas:
            geojson = area.get_coordenadas()
            if geojson:
                feature = {
                    "type": "Feature",
                    "geometry": geojson,
                    "properties": {
                        "id": area.id,
                        "nome": area.nome,
                        "tipo": area.tipo,
                        "tamanho": area.tamanho,
                        "cor": area.cor
                    }
                }
                features.append(feature)
    
    collection = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return jsonify(collection)


@app.route('/api/importar-kml', methods=['POST'])
@login_required
def importar_kml():
    """
    Endpoint para importar arquivos KML/KMZ e extrair coordenadas de polígonos
    
    Retorna um JSON com as coordenadas em formato esperado pelo mapa
    """
    if 'kmlFile' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
    
    file = request.files['kmlFile']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
    # Verificar extensão
    filename = file.filename.lower()
    if not (filename.endswith('.kml') or filename.endswith('.kmz')):
        return jsonify({'success': False, 'message': 'Formato de arquivo inválido. Use KML ou KMZ'})
    
    try:
        if filename.endswith('.kml'):
            # Processar arquivo KML diretamente
            coordenadas = processar_kml(file)
        else:
            # Processar arquivo KMZ (ZIP contendo KML)
            coordenadas = processar_kmz(file)
            
        if not coordenadas:
            return jsonify({'success': False, 'message': 'Nenhum polígono encontrado no arquivo'})
            
        return jsonify({
            'success': True, 
            'coordenadas': coordenadas,
            'message': 'Arquivo importado com sucesso'
        })
            
    except Exception as e:
        logger.error(f"Erro ao processar arquivo KML/KMZ: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'})

@app.route('/api/mapa/animais')
@login_required
def api_mapa_animais():
    animais = Animal.query.filter(
        Animal.ultima_latitude != None,
        Animal.ultima_longitude != None,
        Animal.status == 'Ativo'
    ).all()
    
    features = []
    
    for animal in animais:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [animal.ultima_longitude, animal.ultima_latitude]
            },
            "properties": {
                "id": animal.id,
                "codigo": animal.codigo,
                "nome": animal.nome or f"Animal {animal.codigo}",
                "raca": animal.raca.nome,
                "bateria": animal.bateria,
                "cor": animal.cor,
                "ultima_atualizacao": animal.ultima_atualizacao.isoformat() if animal.ultima_atualizacao else None
            }
        }
        features.append(feature)
    
    collection = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return jsonify(collection)

@app.route('/areas/nova', methods=['GET', 'POST'])
@login_required
def cadastro_area():
    if request.method == 'POST':
        try:
            nome = request.form.get('nome')
            tipo = request.form.get('tipo')
            tamanho = float(request.form.get('tamanho'))
            cor = request.form.get('cor')
            coordenadas = request.form.get('coordenadas')
            
            # Obter propriedade (assumindo que existe apenas uma)
            propriedade = Propriedade.query.first()
            if not propriedade:
                flash('Nenhuma propriedade cadastrada no sistema.', 'danger')
                return redirect(url_for('mapa_propriedade'))
            
            area = Area(
                nome=nome,
                tipo=tipo,
                tamanho=tamanho,
                cor=cor,
                propriedade_id=propriedade.id
            )
            
            # Se coordenadas foram fornecidas, converter de string para lista
            if coordenadas:
                coords_list = json.loads(coordenadas)
                area.set_coordenadas(coords_list)
            
            db.session.add(area)
            db.session.commit()
            
            flash('Área cadastrada com sucesso.', 'success')
            return redirect(url_for('mapa_propriedade'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar área: {str(e)}', 'danger')
            logger.error(f"Erro ao cadastrar área: {str(e)}")
    
    # Obter configurações do mapa
    propriedade = Propriedade.query.first()
    tipo_mapa = 'openstreetmap'  # Padrão
    google_maps_key = ''
    
    if propriedade:
        tipo_mapa = propriedade.tipo_mapa or 'openstreetmap'
        google_maps_key = propriedade.google_maps_key or ''
    
    return render_template(
        'cadastro_area.html',
        tipo_mapa=tipo_mapa,
        google_maps_key=google_maps_key
    )

# Rotas para atividades
@app.route('/atividades')
@login_required
def listar_atividades():
    atividades = Atividade.query.order_by(Atividade.data_inicio.desc()).all()
    return render_template('listar_atividades.html', atividades=atividades)

@app.route('/atividades/nova', methods=['GET', 'POST'])
@login_required
def registrar_atividade():
    if request.method == 'POST':
        try:
            tipo = request.form.get('tipo')
            descricao = request.form.get('descricao')
            data_inicio = datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%dT%H:%M')
            data_fim = None
            if request.form.get('data_fim'):
                data_fim = datetime.strptime(request.form.get('data_fim'), '%Y-%m-%dT%H:%M')
            
            status = request.form.get('status')
            responsavel = request.form.get('responsavel')
            custo = float(request.form.get('custo')) if request.form.get('custo') else None
            observacao = request.form.get('observacao', '')
            area_id = int(request.form.get('area_id')) if request.form.get('area_id') else None
            
            # Obter propriedade (assumindo que existe apenas uma)
            propriedade = Propriedade.query.first()
            if not propriedade:
                flash('Nenhuma propriedade cadastrada no sistema.', 'danger')
                return redirect(url_for('listar_atividades'))
            
            atividade = Atividade(
                tipo=tipo,
                descricao=descricao,
                data_inicio=data_inicio,
                data_fim=data_fim,
                status=status,
                responsavel=responsavel,
                custo=custo,
                observacao=observacao,
                area_id=area_id,
                propriedade_id=propriedade.id
            )
            
            db.session.add(atividade)
            db.session.commit()
            
            flash('Atividade registrada com sucesso.', 'success')
            return redirect(url_for('listar_atividades'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar atividade: {str(e)}', 'danger')
            logger.error(f"Erro ao registrar atividade: {str(e)}")
    
    areas = Area.query.all()
    return render_template('registrar_atividade.html', areas=areas)

# Rotas para relatórios
@app.route('/relatorios')
@login_required
def relatorios():
    # Buscar dados necessários para os filtros dos relatórios
    racas = Raca.query.all()
    areas = Area.query.all()
    
    return render_template(
        'relatorios.html',
        racas=racas,
        areas=areas
    )

@app.route('/relatorios/animais', methods=['POST'])
@login_required
def gerar_relatorio_animais():
    try:
        # Obter os filtros do formulário
        status = request.form.get('status')
        raca_id = request.form.get('raca_id')
        area_id = request.form.get('area_id')
        
        # Construir a consulta com filtros
        query = Animal.query
        
        if status and status != 'Todos':
            query = query.filter_by(status=status)
        
        if raca_id and raca_id != '0':
            query = query.filter_by(raca_id=int(raca_id))
        
        if area_id and area_id != '0':
            query = query.filter_by(area_id=int(area_id))
        
        # Executar a consulta
        animais = query.all()
        
        # Preparar dados para o relatório
        dados = []
        for animal in animais:
            dados.append({
                'Código': animal.codigo,
                'Nome': animal.nome or '',
                'Raça': animal.raca.nome,
                'Sexo': 'Macho' if animal.sexo == 'M' else 'Fêmea',
                'Data Nascimento': animal.data_nascimento.strftime('%d/%m/%Y') if animal.data_nascimento else '',
                'Peso Atual (kg)': animal.peso_atual or 0,  # Evitar valores None
                'Status': animal.status,
                'Área': animal.area.nome if animal.area else 'Não atribuída',
                'Lote': animal.lote.nome if animal.lote else 'Não atribuído'
            })
        
        # Criar DataFrame e exportar para Excel
        if dados:
            df = pd.DataFrame(dados)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Animais', index=False)
                
                # Formatação do arquivo Excel
                workbook = writer.book
                worksheet = writer.sheets['Animais']
                
                # Ajustar largura das colunas
                for idx, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
                    worksheet.set_column(idx, idx, column_width)
                
                # Adicionar formatos
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D8E4BC',
                    'border': 1
                })
                
                # Aplicar formato ao cabeçalho
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
            
            output.seek(0)
            return send_file(
                output,
                as_attachment=True,
                download_name=f'relatorio_animais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('Nenhum dado encontrado para os filtros selecionados.', 'warning')
            return redirect(url_for('relatorios'))
            
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'danger')
        logger.error(f"Erro ao gerar relatório de animais: {str(e)}", exc_info=True)
        return redirect(url_for('relatorios'))

@app.route('/relatorios/atividades', methods=['POST'])
@login_required
def gerar_relatorio_atividades():
    try:
        # Obter os filtros do formulário
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        tipo = request.form.get('tipo')
        status = request.form.get('status')
        
        # Construir a consulta com filtros
        query = Atividade.query
        
        if data_inicio:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Atividade.data_inicio >= data_inicio)
        
        if data_fim:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            # Ajustar para o final do dia
            data_fim = data_fim.replace(hour=23, minute=59, second=59)
            query = query.filter(Atividade.data_inicio <= data_fim)
        
        if tipo and tipo != 'Todos':
            query = query.filter_by(tipo=tipo)
        
        if status and status != 'Todos':
            query = query.filter_by(status=status)
        
        # Executar a consulta
        atividades = query.all()
        
        # Preparar dados para o relatório
        dados = []
        for atividade in atividades:
            dados.append({
                'Tipo': atividade.tipo,
                'Descrição': atividade.descricao,
                'Data Início': atividade.data_inicio.strftime('%d/%m/%Y %H:%M'),
                'Data Fim': atividade.data_fim.strftime('%d/%m/%Y %H:%M') if atividade.data_fim else 'Não concluída',
                'Status': atividade.status,
                'Responsável': atividade.responsavel or 'Não definido',
                'Custo (R$)': atividade.custo if atividade.custo else 0,
                'Área': atividade.area.nome if atividade.area else 'Geral'
            })
        
        # Criar DataFrame e exportar para Excel
        if dados:
            df = pd.DataFrame(dados)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Atividades', index=False)
                
                # Formatação do arquivo Excel
                workbook = writer.book
                worksheet = writer.sheets['Atividades']
                
                # Ajustar largura das colunas
                for idx, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
                    worksheet.set_column(idx, idx, column_width)
                
                # Adicionar formatos
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D8E4BC',
                    'border': 1
                })
                
                # Formato para custos
                money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
                
                # Aplicar formato ao cabeçalho
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Aplicar formato de moeda à coluna de custos
                if 'Custo (R$)' in df.columns:
                    custo_idx = df.columns.get_loc('Custo (R$)')
                    for row_num in range(1, len(df) + 1):  # +1 para pular o cabeçalho
                        worksheet.write_number(row_num, custo_idx, 
                                             float(df.iloc[row_num-1]['Custo (R$)'] or 0), 
                                             money_format)
            
            output.seek(0)
            return send_file(
                output,
                as_attachment=True,
                download_name=f'relatorio_atividades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('Nenhum dado encontrado para os filtros selecionados.', 'warning')
            return redirect(url_for('relatorios'))
            
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'danger')
        logger.error(f"Erro ao gerar relatório de atividades: {str(e)}", exc_info=True)
        return redirect(url_for('relatorios'))

@app.route('/api/dashboard/dados')
@login_required
def api_dashboard_dados():
    try:
        logger.info("Iniciando carregamento de dados do dashboard")
        
        # Total de animais por status
        total_por_status = {
            'Ativo': Animal.query.filter_by(status='Ativo').count(),
            'Vendido': Animal.query.filter_by(status='Vendido').count(),
            'Morto': Animal.query.filter_by(status='Morto').count()
        }
        logger.info(f"Dados de status: {total_por_status}")
        
        # Total de animais por sexo
        total_por_sexo = {
            'Macho': Animal.query.filter_by(sexo='M').count(),
            'Fêmea': Animal.query.filter_by(sexo='F').count()
        }
        logger.info(f"Dados de sexo: {total_por_sexo}")
        
        # Dados de peso médio por raça
        racas = Raca.query.all()
        peso_por_raca = []
        
        for raca in racas:
            animais = Animal.query.filter_by(raca_id=raca.id, status='Ativo').all()
            if animais:
                animais_com_peso = [a for a in animais if a.peso_atual is not None]
                if animais_com_peso:
                    peso_medio = sum(a.peso_atual for a in animais_com_peso) / len(animais_com_peso)
                    peso_por_raca.append({
                        'raca': raca.nome,
                        'peso_medio': round(peso_medio, 2)
                    })
        logger.info(f"Dados de peso por raça: {peso_por_raca}")
        
        # Atividades recentes
        atividades_recentes = []
        atividades = Atividade.query.order_by(Atividade.data_inicio.desc()).limit(5).all()
        
        for atividade in atividades:
            atividades_recentes.append({
                'id': atividade.id,
                'tipo': atividade.tipo,
                'descricao': atividade.descricao,
                'data_inicio': atividade.data_inicio.strftime('%d/%m/%Y'),
                'status': atividade.status
            })
        logger.info(f"Atividades recentes encontradas: {len(atividades_recentes)}")
        
        # Animais por área
        areas = Area.query.all()
        animais_por_area = []
        
        for area in areas:
            total = Animal.query.filter_by(area_id=area.id, status='Ativo').count()
            if total > 0:
                animais_por_area.append({
                    'area': area.nome,
                    'total': total
                })
        logger.info(f"Dados de animais por área: {animais_por_area}")
        
        # Preparar resposta JSON
        resposta = {
            'total_por_status': total_por_status,
            'total_por_sexo': total_por_sexo,
            'peso_por_raca': peso_por_raca,
            'atividades_recentes': atividades_recentes,
            'animais_por_area': animais_por_area
        }
        
        logger.info("Dados do dashboard gerados com sucesso")
        return jsonify(resposta)
    
    except Exception as e:
        logger.error(f"Erro ao gerar dados do dashboard: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Rota para configurações
@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    propriedade = Propriedade.query.first()
    
    if request.method == 'POST':
        try:
            # Determinar o tipo de configuração
            config_type = request.form.get('config_type')
            
            if config_type == 'propriedade':
                # Atualizar ou criar propriedade
                nome = request.form.get('nome')
                inscricao_estadual = request.form.get('inscricao_estadual')
                cpf_cnpj = request.form.get('cpf_cnpj')
                endereco = request.form.get('endereco')
                municipio = request.form.get('municipio')
                estado = request.form.get('estado')
                cep = request.form.get('cep')
                area_total = float(request.form.get('area_total'))
                latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
                longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
                
                # Obter configurações do mapa
                tipo_mapa = request.form.get('tipo_mapa', 'openstreetmap')
                google_maps_key = request.form.get('google_maps_key', '')
                api_token = request.form.get('api_token', '')
                
                # Verificar se deve gerar novo token
                gerar_novo_token = request.form.get('gerar_novo_token') == 'sim'
                
                if propriedade:
                    # Atualiza propriedade existente
                    propriedade.nome = nome
                    propriedade.inscricao_estadual = inscricao_estadual
                    propriedade.cpf_cnpj = cpf_cnpj
                    propriedade.endereco = endereco
                    propriedade.municipio = municipio
                    propriedade.estado = estado
                    propriedade.cep = cep
                    propriedade.area_total = area_total
                    propriedade.latitude = latitude
                    propriedade.longitude = longitude
                    propriedade.tipo_mapa = tipo_mapa
                    propriedade.google_maps_key = google_maps_key
                    
                    # Atualizar ou gerar token de API
                    if gerar_novo_token:
                        import secrets
                        propriedade.api_token = secrets.token_hex(32)
                        flash('Novo token de API gerado com sucesso.', 'success')
                else:
                    # Cria nova propriedade
                    # Gerar token de API para nova propriedade
                    import secrets
                    novo_token = secrets.token_hex(32)
                    
                    propriedade = Propriedade(
                        nome=nome,
                        inscricao_estadual=inscricao_estadual,
                        cpf_cnpj=cpf_cnpj,
                        endereco=endereco,
                        municipio=municipio,
                        estado=estado,
                        cep=cep,
                        area_total=area_total,
                        latitude=latitude,
                        longitude=longitude,
                        tipo_mapa=tipo_mapa,
                        google_maps_key=google_maps_key,
                        api_token=novo_token
                    )
                    db.session.add(propriedade)
                
                db.session.commit()
                flash('Dados da propriedade atualizados com sucesso.', 'success')
            
            elif config_type == 'raca':
                # Adicionar nova raça
                nome = request.form.get('nome')
                especie = request.form.get('especie')
                descricao = request.form.get('descricao', '')
                
                # Verificar se a raça já existe
                raca_existente = Raca.query.filter_by(nome=nome).first()
                if raca_existente:
                    flash('Esta raça já está cadastrada.', 'warning')
                else:
                    raca = Raca(
                        nome=nome,
                        especie=especie,
                        descricao=descricao
                    )
                    db.session.add(raca)
                    db.session.commit()
                    flash('Raça cadastrada com sucesso.', 'success')
            
            elif config_type == 'lote':
                # Adicionar novo lote
                nome = request.form.get('nome')
                tipo = request.form.get('tipo')
                descricao = request.form.get('descricao', '')
                
                lote = Lote(
                    nome=nome,
                    tipo=tipo,
                    descricao=descricao
                )
                db.session.add(lote)
                db.session.commit()
                flash('Lote cadastrado com sucesso.', 'success')
            
            elif config_type == 'usuario':
                # Adicionar novo usuário
                nome = request.form.get('nome')
                email = request.form.get('email')
                senha = request.form.get('senha')
                cargo = request.form.get('cargo')
                
                # Verificar se o e-mail já está em uso
                usuario_existente = Usuario.query.filter_by(email=email).first()
                if usuario_existente:
                    flash('Este e-mail já está em uso.', 'warning')
                else:
                    usuario = Usuario(
                        nome=nome,
                        email=email,
                        cargo=cargo
                    )
                    usuario.set_password(senha)
                    db.session.add(usuario)
                    db.session.commit()
                    flash('Usuário cadastrado com sucesso.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar configurações: {str(e)}', 'danger')
            logger.error(f"Erro ao salvar configurações: {str(e)}")
    
    racas = Raca.query.all()
    lotes = Lote.query.all()
    usuarios = Usuario.query.all()
    
    return render_template(
        'configuracoes.html',
        propriedade=propriedade,
        racas=racas,
        lotes=lotes,
        usuarios=usuarios
    )

# Rota de API para receber dados dos dispositivos LoRa
@app.route('/api/lora/data', methods=['POST'])
def api_lora_data():
    try:
        # Verificar token de autenticação
        auth_token = request.headers.get('X-API-Token')
        if not auth_token:
            return jsonify({'error': 'Token de autenticação não fornecido'}), 401
        
        # Verificar se o token é válido (comparando com o token da propriedade)
        propriedade = Propriedade.query.first()
        if not propriedade or propriedade.api_token != auth_token:
            return jsonify({'error': 'Token de autenticação inválido'}), 401
        
        # Obter dados do payload JSON
        data = request.json
        if not data:
            return jsonify({'error': 'Dados não fornecidos ou formato inválido'}), 400
        
        # Verificar dados mínimos necessários
        device_id = data.get('device_id')
        if not device_id:
            return jsonify({'error': 'ID do dispositivo não fornecido'}), 400
        
        # Buscar dispositivo pelo ID
        dispositivo = DispositivoLora.query.filter_by(device_id=device_id).first()
        if not dispositivo:
            return jsonify({'error': 'Dispositivo não encontrado'}), 404
        
        # Atualizar dados do dispositivo
        dispositivo.ultimo_contato = datetime.now()
        
        # Atualizar bateria se fornecida
        if 'bateria' in data:
            dispositivo.bateria = data.get('bateria')
            
            # Atualizar bateria no animal também
            if dispositivo.animal:
                dispositivo.animal.bateria = data.get('bateria')
        
        # Atualizar firmware se fornecido
        if 'firmware' in data:
            dispositivo.firmware = data.get('firmware')
            
        # Verificar se há dados de localização
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude and longitude and dispositivo.animal:
            # Atualizar localização do animal
            dispositivo.animal.ultima_latitude = latitude
            dispositivo.animal.ultima_longitude = longitude
            dispositivo.animal.ultima_atualizacao = datetime.now()
            
            # Registrar no histórico de localização
            historico = HistoricoLocalizacao(
                animal_id=dispositivo.animal.id,
                device_id=device_id,
                latitude=latitude,
                longitude=longitude,
                bateria=data.get('bateria', dispositivo.bateria)
            )
            db.session.add(historico)
            
        # Salvar todas as alterações
        db.session.commit()
        
        # Retornar resposta de sucesso
        return jsonify({
            'status': 'success',
            'message': 'Dados recebidos e processados com sucesso',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar dados do dispositivo LoRa: {str(e)}")
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

# Erro 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Inicialização do banco de dados com dados de exemplo, se necessário
@app.route('/init_db')
def init_db():
    try:
        # Verifica se já existem dados no banco
        if Usuario.query.count() > 0:
            return "Banco de dados já inicializado."
        
        # Criar usuário admin
        admin = Usuario(
            nome='Administrador',
            email='admin@fazenda.com',
            cargo='Administrador'
        )
        admin.set_password('admin')
        db.session.add(admin)
        
        # Criar propriedade inicial com token de API
        import secrets
        token_inicial = secrets.token_hex(32)
        
        propriedade = Propriedade(
            nome='Fazenda Modelo',
            inscricao_estadual='123456789',
            cpf_cnpj='12345678901234',
            endereco='Estrada Rural, km 10',
            municipio='Campinas',
            estado='SP',
            cep='13000-000',
            area_total=500.0,
            latitude=-22.9064,
            longitude=-47.0616,
            api_token=token_inicial
        )
        db.session.add(propriedade)
        
        # Criar algumas raças
        racas = [
            Raca(nome='Nelore', especie='Bovino', descricao='Raça de corte'),
            Raca(nome='Gir', especie='Bovino', descricao='Raça leiteira'),
            Raca(nome='Holandês', especie='Bovino', descricao='Raça leiteira de alta produção'),
            Raca(nome='Angus', especie='Bovino', descricao='Raça de corte premium')
        ]
        for raca in racas:
            db.session.add(raca)
        
        # Criar algumas áreas
        area1 = Area(
            nome='Pasto Principal',
            tipo='Pasto',
            tamanho=100.0,
            propriedade_id=1,
            cor='#3388ff'
        )
        area1.set_coordenadas([
            [-47.0616, -22.9064],
            [-47.0516, -22.9064],
            [-47.0516, -22.8964],
            [-47.0616, -22.8964],
            [-47.0616, -22.9064]
        ])
        
        area2 = Area(
            nome='Curral',
            tipo='Curral',
            tamanho=5.0,
            propriedade_id=1,
            cor='#ff3333'
        )
        area2.set_coordenadas([
            [-47.0646, -22.9084],
            [-47.0636, -22.9084],
            [-47.0636, -22.9074],
            [-47.0646, -22.9074],
            [-47.0646, -22.9084]
        ])
        
        db.session.add(area1)
        db.session.add(area2)
        
        # Criar alguns lotes
        lotes = [
            Lote(nome='Lote 1', tipo='Engorda', descricao='Animais em fase final de engorda'),
            Lote(nome='Lote 2', tipo='Cria', descricao='Vacas com bezerros'),
            Lote(nome='Lote 3', tipo='Recria', descricao='Animais em crescimento')
        ]
        for lote in lotes:
            db.session.add(lote)
        
        db.session.commit()
        
        # Agora que temos IDs, podemos criar alguns animais
        animais = [
            Animal(
                codigo='BOV001',
                nome='Estrela',
                sexo='F',
                data_nascimento=datetime.now() - timedelta(days=1000),
                peso_atual=450.0,
                raca_id=1,
                propriedade_id=1,
                area_id=1,
                lote_id=1,
                status='Ativo'
            ),
            Animal(
                codigo='BOV002',
                nome='Trovão',
                sexo='M',
                data_nascimento=datetime.now() - timedelta(days=800),
                peso_atual=620.0,
                raca_id=4,
                propriedade_id=1,
                area_id=1,
                lote_id=3,
                status='Ativo'
            ),
            Animal(
                codigo='BOV003',
                nome='Mimosa',
                sexo='F',
                data_nascimento=datetime.now() - timedelta(days=1200),
                peso_atual=480.0,
                raca_id=2,
                propriedade_id=1,
                area_id=1,
                lote_id=2,
                status='Ativo'
            )
        ]
        
        for animal in animais:
            # Adicionar dispositivo LoRa
            animal.gerar_dispositivo_lora()
            # Adicionar coordenadas iniciais aleatórias dentro da propriedade
            animal.ultima_latitude = -22.9064 + (random.random() * 0.01)
            animal.ultima_longitude = -47.0616 + (random.random() * 0.01)
            animal.ultima_atualizacao = datetime.now()
            animal.bateria = random.uniform(60, 100)
            
            db.session.add(animal)
        
        # Adicionar registros de peso para os animais
        for animal in animais:
            # Registros de peso anteriores
            for i in range(5):
                registro = RegistroPeso(
                    peso=animal.peso_atual - random.uniform(5, 20),
                    data_pesagem=datetime.now() - timedelta(days=30 * (i + 1)),
                    animal_id=animal.id,
                    observacao="Pesagem de rotina"
                )
                db.session.add(registro)
        
        # Adicionar algumas atividades
        atividades = [
            Atividade(
                tipo='Vacinação',
                descricao='Vacinação contra febre aftosa',
                data_inicio=datetime.now() - timedelta(days=15),
                data_fim=datetime.now() - timedelta(days=15),
                status='Concluída',
                responsavel='João Silva',
                propriedade_id=1
            ),
            Atividade(
                tipo='Manutenção',
                descricao='Reparo nas cercas do pasto principal',
                data_inicio=datetime.now() - timedelta(days=7),
                status='Em Andamento',
                responsavel='Pedro Oliveira',
                propriedade_id=1,
                area_id=1
            ),
            Atividade(
                tipo='Plantio',
                descricao='Plantio de capim braquiária',
                data_inicio=datetime.now() + timedelta(days=5),
                status='Planejada',
                propriedade_id=1,
                area_id=1
            )
        ]
        
        for atividade in atividades:
            db.session.add(atividade)
        
        # Adicionar dispositivos LoRa
        for animal in animais:
            dispositivo = DispositivoLora(
                device_id=animal.id_dispositivo,
                tipo='Brinco',
                animal_id=animal.id,
                ultimo_contato=datetime.now(),
                status='Ativo',
                bateria=animal.bateria,
                firmware='1.0.0'
            )
            db.session.add(dispositivo)
        
        # Adicionar histórico de localização para os animais
        for animal in animais:
            for i in range(10):
                historico = HistoricoLocalizacao(
                    animal_id=animal.id,
                    device_id=animal.id_dispositivo,
                    latitude=animal.ultima_latitude - (random.random() * 0.002),
                    longitude=animal.ultima_longitude - (random.random() * 0.002),
                    data_hora=datetime.now() - timedelta(hours=i * 2),
                    bateria=min(100, animal.bateria + (i * 2))
                )
                db.session.add(historico)
        
        # Adicionar estações meteorológicas
        estacoes = [
            EstacaoMeteorologica(
                codigo='EST001',
                nome='Estação Central',
                descricao='Estação meteorológica principal, localizada próxima à sede da fazenda',
                modelo='WeatherMaster Pro 7000',
                fabricante='TechWeather',
                data_instalacao=datetime.now() - timedelta(days=180),
                latitude=propriedade.latitude + 0.002 if propriedade.latitude else -23.5505,
                longitude=propriedade.longitude + 0.002 if propriedade.longitude else -46.6333,
                altitude=750.5,
                status='Ativo',
                intervalo_leitura=15,
                sensor_temperatura=True,
                sensor_umidade=True,
                sensor_pressao=True,
                sensor_vento=True,
                sensor_chuva=True,
                sensor_radiacao=True,
                sensor_solo=False,
                propriedade_id=propriedade.id
            ),
            EstacaoMeteorologica(
                codigo='EST002',
                nome='Estação Pasto Sul',
                descricao='Estação meteorológica secundária, instalada no pasto sul para monitoramento específico',
                modelo='WeatherMaster Lite 5000',
                fabricante='TechWeather',
                data_instalacao=datetime.now() - timedelta(days=90),
                latitude=propriedade.latitude - 0.005 if propriedade.latitude else -23.5605,
                longitude=propriedade.longitude - 0.003 if propriedade.longitude else -46.6433,
                altitude=735.0,
                status='Ativo',
                intervalo_leitura=30,
                sensor_temperatura=True,
                sensor_umidade=True,
                sensor_pressao=False,
                sensor_vento=True,
                sensor_chuva=True,
                sensor_radiacao=False,
                sensor_solo=True,
                propriedade_id=propriedade.id
            )
        ]
        
        for estacao in estacoes:
            # Gerar ID de dispositivo LoRa para cada estação
            estacao.gerar_device_id()
            estacao.firmware = '1.2.0'
            estacao.bateria = 85.5
            estacao.ultimo_contato = datetime.now() - timedelta(hours=random.randint(1, 12))
            db.session.add(estacao)
            
            # Adicionar algumas leituras para cada estação
            for i in range(48):  # 48 horas de histórico
                hora = datetime.now() - timedelta(hours=i)
                
                # Simular valores baseados na hora do dia
                temp_base = 25 - (10 if 0 <= hora.hour <= 6 else 0)  # Mais frio de madrugada
                umid_base = 70 + (10 if 0 <= hora.hour <= 6 else 0)  # Mais úmido de madrugada
                
                leitura = LeituraMeteorologica(
                    estacao_id=estacao.id,
                    data_hora=hora,
                    temperatura=temp_base + random.uniform(-2, 2) if estacao.sensor_temperatura else None,
                    umidade=umid_base + random.uniform(-5, 5) if estacao.sensor_umidade else None,
                    pressao=1015 + random.uniform(-5, 5) if estacao.sensor_pressao else None,
                    velocidade_vento=random.uniform(0, 15) if estacao.sensor_vento else None,
                    direcao_vento=random.uniform(0, 360) if estacao.sensor_vento else None,
                    precipitacao=(5 if 12 <= hora.hour <= 18 else 0) + random.uniform(0, 2) if estacao.sensor_chuva else None,
                    radiacao_solar=(800 if 10 <= hora.hour <= 14 else 200) + random.uniform(-50, 50) if estacao.sensor_radiacao else None,
                    umidade_solo=30 + random.uniform(-5, 5) if estacao.sensor_solo else None,
                    temperatura_solo=22 + random.uniform(-2, 2) if estacao.sensor_solo else None,
                    bateria=min(100, estacao.bateria + i * 0.3),
                    sinal_lora=-75 + random.uniform(-10, 10)
                )
                db.session.add(leitura)
        
            # Adicionar alguns alertas
            if estacao.sensor_temperatura:
                alerta = AlertaMeteorologico(
                    estacao_id=estacao.id,
                    tipo='Temperatura Alta',
                    descricao='Temperatura acima do limite estabelecido',
                    data_hora=datetime.now() - timedelta(days=1, hours=3),
                    nivel='Atenção',
                    valor_medido=32.5,
                    valor_limite=30.0,
                    unidade='°C',
                    status='Finalizado'
                )
                db.session.add(alerta)
            
            if estacao.sensor_chuva:
                alerta = AlertaMeteorologico(
                    estacao_id=estacao.id,
                    tipo='Chuva Forte',
                    descricao='Precipitação acima do limite estabelecido',
                    data_hora=datetime.now() - timedelta(hours=12),
                    nivel='Alerta',
                    valor_medido=15.8,
                    valor_limite=10.0,
                    unidade='mm',
                    status='Ativo'
                )
                db.session.add(alerta)
        
        db.session.commit()
        return "Banco de dados inicializado com sucesso!"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        return f"Erro ao inicializar banco de dados: {str(e)}"

# Rotas para gerenciamento de estações meteorológicas
@app.route('/estacoes-meteorologicas')
@login_required
def listar_estacoes():
    estacoes = EstacaoMeteorologica.query.all()
    return render_template('listar_estacoes.html', estacoes=estacoes)

@app.route('/estacoes-meteorologicas/nova', methods=['GET', 'POST'])
@login_required
def cadastro_estacao():
    if request.method == 'POST':
        try:
            codigo = request.form.get('codigo')
            nome = request.form.get('nome')
            modelo = request.form.get('modelo')
            fabricante = request.form.get('fabricante')
            descricao = request.form.get('descricao')
            
            # Processar data de instalação se fornecida
            data_instalacao = request.form.get('data_instalacao')
            if data_instalacao:
                data_instalacao = datetime.strptime(data_instalacao, '%Y-%m-%d')
            else:
                data_instalacao = None
            
            # Processar intervalo de leitura
            intervalo_leitura = int(request.form.get('intervalo_leitura', 15))
            
            # Processar coordenadas se fornecidas
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            altitude = request.form.get('altitude')
            
            if latitude:
                latitude = float(latitude)
            if longitude:
                longitude = float(longitude)
            if altitude:
                altitude = float(altitude)
            
            # Verificar quais sensores estão disponíveis
            sensor_temperatura = 'sensor_temperatura' in request.form
            sensor_umidade = 'sensor_umidade' in request.form
            sensor_pressao = 'sensor_pressao' in request.form
            sensor_vento = 'sensor_vento' in request.form
            sensor_chuva = 'sensor_chuva' in request.form
            sensor_radiacao = 'sensor_radiacao' in request.form
            sensor_solo = 'sensor_solo' in request.form
            
            # Obter propriedade
            propriedade = Propriedade.query.first()
            if not propriedade:
                flash('Nenhuma propriedade cadastrada no sistema.', 'danger')
                return redirect(url_for('listar_estacoes'))
            
            # Criar a estação
            estacao = EstacaoMeteorologica(
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                modelo=modelo,
                fabricante=fabricante,
                data_instalacao=data_instalacao,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                intervalo_leitura=intervalo_leitura,
                sensor_temperatura=sensor_temperatura,
                sensor_umidade=sensor_umidade,
                sensor_pressao=sensor_pressao,
                sensor_vento=sensor_vento,
                sensor_chuva=sensor_chuva,
                sensor_radiacao=sensor_radiacao,
                sensor_solo=sensor_solo,
                propriedade_id=propriedade.id
            )
            
            # Gerar dispositivo LoRa se solicitado
            if request.form.get('gerar_dispositivo') == 'sim':
                estacao.gerar_device_id()
                estacao.firmware = '1.0.0'
            
            db.session.add(estacao)
            db.session.commit()
            
            flash('Estação meteorológica cadastrada com sucesso.', 'success')
            return redirect(url_for('listar_estacoes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar estação: {str(e)}', 'danger')
            logger.error(f"Erro ao cadastrar estação: {str(e)}")
    
    return render_template('cadastro_estacao.html')

@app.route('/estacoes-meteorologicas/<int:id>')
@login_required
def detalhes_estacao(id):
    estacao = EstacaoMeteorologica.query.get_or_404(id)
    
    # Buscar última leitura
    ultima_leitura = LeituraMeteorologica.query.filter_by(estacao_id=id).order_by(LeituraMeteorologica.data_hora.desc()).first()
    
    # Buscar histórico de leituras (últimas 100)
    leituras = LeituraMeteorologica.query.filter_by(estacao_id=id).order_by(LeituraMeteorologica.data_hora.desc()).limit(100).all()
    
    # Buscar alertas ativos
    alertas = AlertaMeteorologico.query.filter_by(estacao_id=id).filter(AlertaMeteorologico.status != 'Finalizado').order_by(AlertaMeteorologico.data_hora.desc()).all()
    
    return render_template(
        'detalhes_estacao.html',
        estacao=estacao,
        ultima_leitura=ultima_leitura,
        leituras=leituras,
        alertas=alertas
    )

@app.route('/estacoes-meteorologicas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_estacao(id):
    estacao = EstacaoMeteorologica.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Atualizar dados básicos
            estacao.codigo = request.form.get('codigo')
            estacao.nome = request.form.get('nome')
            estacao.modelo = request.form.get('modelo')
            estacao.fabricante = request.form.get('fabricante')
            estacao.descricao = request.form.get('descricao')
            estacao.status = request.form.get('status')
            
            # Processar data de instalação se fornecida
            data_instalacao = request.form.get('data_instalacao')
            if data_instalacao:
                estacao.data_instalacao = datetime.strptime(data_instalacao, '%Y-%m-%d')
            else:
                estacao.data_instalacao = None
            
            # Processar intervalo de leitura
            estacao.intervalo_leitura = int(request.form.get('intervalo_leitura', 15))
            
            # Processar coordenadas se fornecidas
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            altitude = request.form.get('altitude')
            
            if latitude:
                estacao.latitude = float(latitude)
            else:
                estacao.latitude = None
                
            if longitude:
                estacao.longitude = float(longitude)
            else:
                estacao.longitude = None
                
            if altitude:
                estacao.altitude = float(altitude)
            else:
                estacao.altitude = None
            
            # Atualizar sensores disponíveis
            estacao.sensor_temperatura = 'sensor_temperatura' in request.form
            estacao.sensor_umidade = 'sensor_umidade' in request.form
            estacao.sensor_pressao = 'sensor_pressao' in request.form
            estacao.sensor_vento = 'sensor_vento' in request.form
            estacao.sensor_chuva = 'sensor_chuva' in request.form
            estacao.sensor_radiacao = 'sensor_radiacao' in request.form
            estacao.sensor_solo = 'sensor_solo' in request.form
            
            # Processar dispositivo LoRa
            if not estacao.device_id and request.form.get('gerar_dispositivo') == 'sim':
                # Gerar novo dispositivo
                estacao.gerar_device_id()
                estacao.firmware = '1.0.0'
            elif estacao.device_id and request.form.get('remover_dispositivo') == 'sim':
                # Remover dispositivo
                estacao.device_id = None
                estacao.firmware = None
                estacao.bateria = None
                estacao.ultimo_contato = None
            
            db.session.commit()
            flash('Estação meteorológica atualizada com sucesso.', 'success')
            return redirect(url_for('detalhes_estacao', id=estacao.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar estação: {str(e)}', 'danger')
            logger.error(f"Erro ao atualizar estação: {str(e)}")
    
    return render_template('editar_estacao.html', estacao=estacao)

@app.route('/estacoes-meteorologicas/<int:id>/solicitar-leitura', methods=['POST'])
@login_required
def solicitar_leitura(id):
    estacao = EstacaoMeteorologica.query.get_or_404(id)
    
    if not estacao.device_id:
        flash('Esta estação não possui dispositivo LoRa configurado.', 'warning')
        return redirect(url_for('detalhes_estacao', id=id))
    
    try:
        # Conectar ao gateway LoRa (se necessário)
        if not lora_manager.gateway_connected:
            lora_manager.connect_to_gateway()
        
        # Em um sistema real, enviaríamos um comando para o dispositivo
        # Aqui vamos simular uma leitura
        
        # Gerar dados simulados para a estação
        dados = {
            'temperatura': round(random.uniform(15, 30), 1) if estacao.sensor_temperatura else None,
            'umidade': round(random.uniform(30, 90), 1) if estacao.sensor_umidade else None,
            'pressao': round(random.uniform(980, 1030), 1) if estacao.sensor_pressao else None,
            'velocidade_vento': round(random.uniform(0, 25), 1) if estacao.sensor_vento else None,
            'direcao_vento': round(random.uniform(0, 360), 1) if estacao.sensor_vento else None,
            'precipitacao': round(random.uniform(0, 5), 1) if estacao.sensor_chuva else None,
            'radiacao_solar': round(random.uniform(0, 1000), 1) if estacao.sensor_radiacao else None,
            'umidade_solo': round(random.uniform(5, 40), 1) if estacao.sensor_solo else None,
            'temperatura_solo': round(random.uniform(10, 25), 1) if estacao.sensor_solo else None,
            'bateria': min(100, (estacao.bateria or 90) - random.uniform(0, 2)),
            'sinal_lora': round(random.uniform(-100, -60), 1)
        }
        
        # Criar registro da leitura
        leitura = LeituraMeteorologica(
            estacao_id=id,
            temperatura=dados['temperatura'],
            umidade=dados['umidade'],
            pressao=dados['pressao'],
            velocidade_vento=dados['velocidade_vento'],
            direcao_vento=dados['direcao_vento'],
            precipitacao=dados['precipitacao'],
            radiacao_solar=dados['radiacao_solar'],
            umidade_solo=dados['umidade_solo'],
            temperatura_solo=dados['temperatura_solo'],
            bateria=dados['bateria'],
            sinal_lora=dados['sinal_lora']
        )
        
        # Atualizar dados da estação
        estacao.ultimo_contato = datetime.now()
        estacao.bateria = dados['bateria']
        
        # Verificar se deve gerar alertas
        # Exemplo: alerta de temperatura alta
        if estacao.sensor_temperatura and dados['temperatura'] > 30:
            alerta = AlertaMeteorologico(
                estacao_id=id,
                tipo='Temperatura Alta',
                descricao=f'Temperatura acima do limite estabelecido',
                nivel='Atenção',
                valor_medido=dados['temperatura'],
                valor_limite=30,
                unidade='°C'
            )
            db.session.add(alerta)
        
        # Exemplo: alerta de chuva forte
        if estacao.sensor_chuva and dados['precipitacao'] > 10:
            alerta = AlertaMeteorologico(
                estacao_id=id,
                tipo='Chuva Forte',
                descricao=f'Precipitação acima do limite estabelecido',
                nivel='Alerta',
                valor_medido=dados['precipitacao'],
                valor_limite=10,
                unidade='mm'
            )
            db.session.add(alerta)
        
        db.session.add(leitura)
        db.session.commit()
        
        flash('Leitura da estação solicitada com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao solicitar leitura: {str(e)}', 'danger')
        logger.error(f"Erro ao solicitar leitura da estação: {str(e)}")
    
    return redirect(url_for('detalhes_estacao', id=id))

@app.route('/estacoes-meteorologicas/<int:id>/leitura-manual', methods=['POST'])
@login_required
def registrar_leitura_manual(id):
    estacao = EstacaoMeteorologica.query.get_or_404(id)
    
    try:
        # Processar dados do formulário
        dados = {}
        
        if estacao.sensor_temperatura and request.form.get('temperatura'):
            dados['temperatura'] = float(request.form.get('temperatura'))
        
        if estacao.sensor_umidade and request.form.get('umidade'):
            dados['umidade'] = float(request.form.get('umidade'))
        
        if estacao.sensor_pressao and request.form.get('pressao'):
            dados['pressao'] = float(request.form.get('pressao'))
        
        if estacao.sensor_vento:
            if request.form.get('velocidade_vento'):
                dados['velocidade_vento'] = float(request.form.get('velocidade_vento'))
            if request.form.get('direcao_vento'):
                dados['direcao_vento'] = float(request.form.get('direcao_vento'))
        
        if estacao.sensor_chuva and request.form.get('precipitacao'):
            dados['precipitacao'] = float(request.form.get('precipitacao'))
        
        if estacao.sensor_radiacao and request.form.get('radiacao_solar'):
            dados['radiacao_solar'] = float(request.form.get('radiacao_solar'))
        
        if estacao.sensor_solo:
            if request.form.get('umidade_solo'):
                dados['umidade_solo'] = float(request.form.get('umidade_solo'))
            if request.form.get('temperatura_solo'):
                dados['temperatura_solo'] = float(request.form.get('temperatura_solo'))
        
        # Criar leitura manual
        leitura = LeituraMeteorologica(
            estacao_id=id,
            temperatura=dados.get('temperatura'),
            umidade=dados.get('umidade'),
            pressao=dados.get('pressao'),
            velocidade_vento=dados.get('velocidade_vento'),
            direcao_vento=dados.get('direcao_vento'),
            precipitacao=dados.get('precipitacao'),
            radiacao_solar=dados.get('radiacao_solar'),
            umidade_solo=dados.get('umidade_solo'),
            temperatura_solo=dados.get('temperatura_solo')
        )
        
        db.session.add(leitura)
        db.session.commit()
        
        flash('Leitura manual registrada com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar leitura manual: {str(e)}', 'danger')
        logger.error(f"Erro ao registrar leitura manual: {str(e)}")
    
    return redirect(url_for('detalhes_estacao', id=id))

@app.route('/criar_estacoes_exemplo')
def criar_estacoes_exemplo():
    try:
        # Verificar se há propriedade
        propriedade = Propriedade.query.first()
        if not propriedade:
            return "Primeira inicialize o banco de dados através da rota /init_db"
        
        # Adicionar estações meteorológicas
        estacoes = [
            EstacaoMeteorologica(
                codigo='EST001',
                nome='Estação Central',
                descricao='Estação meteorológica principal, localizada próxima à sede da fazenda',
                modelo='WeatherMaster Pro 7000',
                fabricante='TechWeather',
                data_instalacao=datetime.now() - timedelta(days=180),
                latitude=propriedade.latitude + 0.002 if propriedade.latitude else -23.5505,
                longitude=propriedade.longitude + 0.002 if propriedade.longitude else -46.6333,
                altitude=750.5,
                status='Ativo',
                intervalo_leitura=15,
                sensor_temperatura=True,
                sensor_umidade=True,
                sensor_pressao=True,
                sensor_vento=True,
                sensor_chuva=True,
                sensor_radiacao=True,
                sensor_solo=False,
                propriedade_id=propriedade.id
            ),
            EstacaoMeteorologica(
                codigo='EST002',
                nome='Estação Pasto Sul',
                descricao='Estação meteorológica secundária, instalada no pasto sul para monitoramento específico',
                modelo='WeatherMaster Lite 5000',
                fabricante='TechWeather',
                data_instalacao=datetime.now() - timedelta(days=90),
                latitude=propriedade.latitude - 0.005 if propriedade.latitude else -23.5605,
                longitude=propriedade.longitude - 0.003 if propriedade.longitude else -46.6433,
                altitude=735.0,
                status='Ativo',
                intervalo_leitura=30,
                sensor_temperatura=True,
                sensor_umidade=True,
                sensor_pressao=False,
                sensor_vento=True,
                sensor_chuva=True,
                sensor_radiacao=False,
                sensor_solo=True,
                propriedade_id=propriedade.id
            )
        ]
        
        for estacao in estacoes:
            # Gerar ID de dispositivo LoRa para cada estação
            estacao.gerar_device_id()
            estacao.firmware = '1.2.0'
            estacao.bateria = 85.5
            estacao.ultimo_contato = datetime.now() - timedelta(hours=random.randint(1, 12))
            db.session.add(estacao)
            
            # Adicionar algumas leituras para cada estação
            for i in range(48):  # 48 horas de histórico
                hora = datetime.now() - timedelta(hours=i)
                
                # Simular valores baseados na hora do dia
                temp_base = 25 - (10 if 0 <= hora.hour <= 6 else 0)  # Mais frio de madrugada
                umid_base = 70 + (10 if 0 <= hora.hour <= 6 else 0)  # Mais úmido de madrugada
                
                leitura = LeituraMeteorologica(
                    estacao_id=estacao.id,
                    data_hora=hora,
                    temperatura=temp_base + random.uniform(-2, 2) if estacao.sensor_temperatura else None,
                    umidade=umid_base + random.uniform(-5, 5) if estacao.sensor_umidade else None,
                    pressao=1015 + random.uniform(-5, 5) if estacao.sensor_pressao else None,
                    velocidade_vento=random.uniform(0, 15) if estacao.sensor_vento else None,
                    direcao_vento=random.uniform(0, 360) if estacao.sensor_vento else None,
                    precipitacao=(5 if 12 <= hora.hour <= 18 else 0) + random.uniform(0, 2) if estacao.sensor_chuva else None,
                    radiacao_solar=(800 if 10 <= hora.hour <= 14 else 200) + random.uniform(-50, 50) if estacao.sensor_radiacao else None,
                    umidade_solo=30 + random.uniform(-5, 5) if estacao.sensor_solo else None,
                    temperatura_solo=22 + random.uniform(-2, 2) if estacao.sensor_solo else None,
                    bateria=min(100, estacao.bateria + i * 0.3),
                    sinal_lora=-75 + random.uniform(-10, 10)
                )
                db.session.add(leitura)
        
            # Adicionar alguns alertas
            if estacao.sensor_temperatura:
                alerta = AlertaMeteorologico(
                    estacao_id=estacao.id,
                    tipo='Temperatura Alta',
                    descricao='Temperatura acima do limite estabelecido',
                    data_hora=datetime.now() - timedelta(days=1, hours=3),
                    nivel='Atenção',
                    valor_medido=32.5,
                    valor_limite=30.0,
                    unidade='°C',
                    status='Finalizado'
                )
                db.session.add(alerta)
            
            if estacao.sensor_chuva:
                alerta = AlertaMeteorologico(
                    estacao_id=estacao.id,
                    tipo='Chuva Forte',
                    descricao='Precipitação acima do limite estabelecido',
                    data_hora=datetime.now() - timedelta(hours=12),
                    nivel='Alerta',
                    valor_medido=15.8,
                    valor_limite=10.0,
                    unidade='mm',
                    status='Ativo'
                )
                db.session.add(alerta)
        
        db.session.commit()
        return "Estações meteorológicas de exemplo criadas com sucesso!"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar estações de exemplo: {str(e)}")
        return f"Erro ao criar estações de exemplo: {str(e)}"
        
@app.route('/criar_exemplos')
def criar_exemplos():
    try:
        # Verificar se há propriedade
        propriedade = Propriedade.query.first()
        if not propriedade:
            return "Primeira inicialize o banco de dados através da rota /init_db"
            
        # Identificar IDs necessários
        racas = Raca.query.all()
        raca_nelore = next((r for r in racas if r.nome == 'Nelore'), racas[0])
        raca_angus = next((r for r in racas if r.nome == 'Angus'), racas[-1])
        
        areas = Area.query.all()
        area_pasto = areas[0]
        area_curral = areas[1] if len(areas) > 1 else areas[0]
        
        lotes = Lote.query.all()
        lote_engorda = lotes[0]
        
        # Criar novos animais com dispositivos LoRa
        novos_animais = [
            Animal(
                codigo='BOV004',
                nome='Valente',
                sexo='M',
                data_nascimento=datetime.now() - timedelta(days=550),
                peso_atual=580.0,
                raca_id=raca_nelore.id,
                propriedade_id=propriedade.id,
                area_id=area_pasto.id,
                lote_id=lote_engorda.id,
                status='Ativo'
            ),
            Animal(
                codigo='BOV005',
                nome='Bandido',
                sexo='M',
                data_nascimento=datetime.now() - timedelta(days=680),
                peso_atual=650.0,
                raca_id=raca_angus.id,
                propriedade_id=propriedade.id,
                area_id=area_pasto.id,
                lote_id=lote_engorda.id,
                status='Ativo'
            ),
            Animal(
                codigo='BOV006',
                nome='Joia',
                sexo='F',
                data_nascimento=datetime.now() - timedelta(days=900),
                peso_atual=520.0,
                raca_id=raca_nelore.id,
                propriedade_id=propriedade.id,
                area_id=area_curral.id,
                lote_id=lote_engorda.id,
                status='Ativo'
            ),
            Animal(
                codigo='BOV007',
                nome='Botafogo',
                sexo='M',
                data_nascimento=datetime.now() - timedelta(days=730),
                peso_atual=670.0,
                raca_id=raca_angus.id,
                propriedade_id=propriedade.id,
                area_id=area_pasto.id,
                lote_id=lote_engorda.id,
                status='Ativo'
            ),
            Animal(
                codigo='BOV008',
                nome='Mansinha',
                sexo='F',
                data_nascimento=datetime.now() - timedelta(days=820),
                peso_atual=515.0,
                raca_id=raca_nelore.id,
                propriedade_id=propriedade.id,
                area_id=area_pasto.id,
                lote_id=lote_engorda.id,
                status='Ativo'
            )
        ]
        
        for animal in novos_animais:
            # Adicionar dispositivo LoRa
            animal.gerar_dispositivo_lora()
            # Adicionar coordenadas iniciais aleatórias dentro da propriedade
            animal.ultima_latitude = propriedade.latitude + (random.random() * 0.01)
            animal.ultima_longitude = propriedade.longitude + (random.random() * 0.01)
            animal.ultima_atualizacao = datetime.now()
            animal.bateria = random.uniform(60, 100)
            
            db.session.add(animal)
            
        db.session.flush()  # Para gerar os IDs antes de continuar
        
        # Adicionar dispositivos LoRa
        dispositivos_lora = []
        for animal in novos_animais:
            dispositivo = DispositivoLora(
                device_id=animal.id_dispositivo,
                tipo='Brinco Eletrônico',
                animal_id=animal.id,
                ultimo_contato=datetime.now(),
                status='Ativo',
                bateria=animal.bateria,
                firmware='1.2.0'
            )
            dispositivos_lora.append(dispositivo)
            db.session.add(dispositivo)
        
        # Adicionar histórico de localização para os novos animais
        for animal in novos_animais:
            for i in range(10):
                historico = HistoricoLocalizacao(
                    animal_id=animal.id,
                    device_id=animal.id_dispositivo,
                    latitude=animal.ultima_latitude - (random.random() * 0.002),
                    longitude=animal.ultima_longitude - (random.random() * 0.002),
                    data_hora=datetime.now() - timedelta(hours=i * 2),
                    bateria=min(100, animal.bateria + (i * 2))
                )
                db.session.add(historico)
        
        # Adicionando registros de peso
        for animal in novos_animais:
            for i in range(5):
                peso = animal.peso_atual - random.uniform(5, 20)
                registro = RegistroPeso(
                    peso=peso,
                    data_pesagem=datetime.now() - timedelta(days=30 * (i + 1)),
                    animal_id=animal.id,
                    observacao="Pesagem periódica"
                )
                db.session.add(registro)
        
        # Adicionar registros sanitários
        for animal in novos_animais:
            registro1 = RegistroSanitario(
                tipo='Vacinação',
                produto='Vacina Contra Febre Aftosa',
                dose=5.0,
                unidade_dose='ml',
                data_aplicacao=datetime.now() - timedelta(days=90),
                data_proxima=datetime.now() + timedelta(days=275),
                responsavel='José Pereira',
                observacao='Aplicação semestral obrigatória',
                animal_id=animal.id
            )
            
            registro2 = RegistroSanitario(
                tipo='Vermifugação',
                produto='Ivermectina 1%',
                dose=10.0,
                unidade_dose='ml',
                data_aplicacao=datetime.now() - timedelta(days=45),
                data_proxima=datetime.now() + timedelta(days=135),
                responsavel='Maria Silva',
                observacao='Controle parasitário trimestral',
                animal_id=animal.id
            )
            
            db.session.add(registro1)
            db.session.add(registro2)
            
        db.session.commit()
        
        # Resumo dos dados criados para retornar ao usuário
        resumo = {
            'total_animais': len(novos_animais),
            'dispositivos_lora': len(dispositivos_lora),
            'animais': [
                f"BOV{i+4:03d} - {a.nome} ({a.sexo}) - {a.raca.nome} - {a.peso_atual}kg" 
                for i, a in enumerate(novos_animais)
            ]
        }
        
        return jsonify({
            'mensagem': 'Exemplos criados com sucesso!',
            'dados': resumo
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar exemplos: {str(e)}")
        return f"Erro ao criar exemplos: {str(e)}"

@app.route('/api/estacao/<int:id>/leituras')
@login_required
def api_estacao_leituras(id):
    """API para obter o histórico de leituras de uma estação."""
    try:
        # Verificar se a estação existe
        estacao = EstacaoMeteorologica.query.get_or_404(id)
        
        # Buscar as leituras da estação
        leituras = LeituraMeteorologica.query.filter_by(estacao_id=id)\
            .order_by(LeituraMeteorologica.data_hora.desc())\
            .all()
        
        # Preparar a resposta
        response = {
            'estacao': {
                'id': estacao.id,
                'nome': estacao.nome,
                'codigo': estacao.codigo
            },
            'leituras': [{
                'id': leitura.id,
                'data_hora': leitura.data_hora.isoformat(),
                'temperatura': leitura.temperatura,
                'umidade': leitura.umidade,
                'pressao': leitura.pressao,
                'velocidade_vento': leitura.velocidade_vento,
                'direcao_vento': leitura.direcao_vento,
                'precipitacao': leitura.precipitacao,
                'radiacao_solar': leitura.radiacao_solar,
                'umidade_solo': leitura.umidade_solo,
                'temperatura_solo': leitura.temperatura_solo,
                'bateria': leitura.bateria,
                'sinal_lora': leitura.sinal_lora
            } for leitura in leituras]
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Erro ao obter leituras da estação {id}: {str(e)}")
        return jsonify({'erro': f"Erro ao obter leituras: {str(e)}"}), 500
