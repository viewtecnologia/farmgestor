from app import app

# Importar rotas e módulos
import routes 
import criar_estacoes_exemplo_rotas  # Importando as novas rotas para estações meteorológicas
import api_rotas  # Importando as rotas da API para dispositivos LoRa e balanças

# Inicializar a API
api_rotas.init_app(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
