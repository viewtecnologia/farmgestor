import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Configuração de logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Inicialização do SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configuração do banco de dados
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicialização do banco de dados
db.init_app(app)

# Inicialização do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

# Criação das tabelas no banco de dados
with app.app_context():
    # Importação dos modelos
    import models  # noqa: F401
    db.create_all()

# Importação das rotas
from routes import *  # noqa: F401
