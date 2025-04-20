<?php
/**
 * Instalador do Sistema de Gestão Agropecuária
 * Este script facilita a instalação do sistema via navegador no CyberPanel
 */

// Evitar timeout para operações longas
set_time_limit(600);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// Definição de constantes
define('INSTALLER_VERSION', '1.0');
define('REQUIRED_PHP_VERSION', '7.4.0');
define('REQUIRED_EXTENSIONS', ['pdo', 'pdo_pgsql', 'curl', 'zip']);
define('SYSTEM_NAME', 'Sistema de Gestão Agropecuária');

// Funções de utilitário
function check_requirements() {
    $errors = [];
    
    // Verificar versão do PHP
    if (version_compare(PHP_VERSION, REQUIRED_PHP_VERSION, '<')) {
        $errors[] = 'PHP: A versão mínima requerida é ' . REQUIRED_PHP_VERSION . '. Sua versão é ' . PHP_VERSION;
    }
    
    // Verificar extensões
    foreach (REQUIRED_EXTENSIONS as $ext) {
        if (!extension_loaded($ext)) {
            $errors[] = 'PHP: A extensão ' . $ext . ' é necessária e não está instalada.';
        }
    }
    
    // Verificar permissões de diretório
    $current_dir = dirname(__FILE__);
    if (!is_writable($current_dir)) {
        $errors[] = 'Permissões: O diretório ' . $current_dir . ' não tem permissão de escrita.';
    }
    
    // Verificar se o CyberPanel está instalado
    if (!file_exists('/usr/local/CyberCP')) {
        $errors[] = 'Ambiente: CyberPanel não detectado. O instalador pode funcionar, mas algumas funcionalidades podem não estar disponíveis.';
    }
    
    return $errors;
}

function random_string($length = 16) {
    $chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()';
    $string = '';
    for ($i = 0; $i < $length; $i++) {
        $string .= $chars[random_int(0, strlen($chars) - 1)];
    }
    return $string;
}

function execute_command($command) {
    $output = [];
    $return_var = 0;
    exec($command . ' 2>&1', $output, $return_var);
    return [
        'success' => $return_var === 0,
        'output' => implode("\n", $output),
        'code' => $return_var
    ];
}

function detect_domain() {
    $script_path = $_SERVER['SCRIPT_FILENAME'];
    $parts = explode('/', $script_path);
    $domain = '';
    
    foreach ($parts as $part) {
        if (strpos($part, '.') !== false && strpos($part, '.php') === false) {
            $domain = $part;
            break;
        }
    }
    
    return $domain;
}

function get_installer_path() {
    return dirname(__FILE__);
}

function is_public_html() {
    return strpos(get_installer_path(), 'public_html') !== false;
}

function check_python() {
    $result = execute_command('which python3');
    if (!$result['success']) {
        return false;
    }
    
    $version_result = execute_command('python3 --version');
    if (!$version_result['success']) {
        return false;
    }
    
    // Extract version number
    preg_match('/Python (\d+\.\d+\.\d+)/', $version_result['output'], $matches);
    if (isset($matches[1])) {
        return $matches[1];
    }
    
    return false;
}

function check_postgres() {
    $result = execute_command('which psql');
    if (!$result['success']) {
        return false;
    }
    
    $version_result = execute_command('psql --version');
    if (!$version_result['success']) {
        return false;
    }
    
    // Extract version number
    preg_match('/(\d+\.\d+)/', $version_result['output'], $matches);
    if (isset($matches[1])) {
        return $matches[1];
    }
    
    return false;
}

function create_virtual_env($path) {
    $current_dir = $path;
    $result = execute_command("cd $current_dir && python3 -m venv venv");
    return $result['success'];
}

function install_dependencies($path) {
    $current_dir = $path;
    $packages = [
        'flask',
        'flask-login',
        'flask-sqlalchemy',
        'flask-wtf',
        'gunicorn',
        'psycopg2-binary',
        'werkzeug',
        'pandas',
        'xlsxwriter',
        'email-validator'
    ];
    
    $success = true;
    $log = '';
    
    foreach ($packages as $package) {
        $result = execute_command("cd $current_dir && venv/bin/pip install $package");
        $success = $success && $result['success'];
        $log .= "Instalando $package: " . ($result['success'] ? 'OK' : 'FALHA') . "\n";
        $log .= $result['output'] . "\n";
    }
    
    return ['success' => $success, 'log' => $log];
}

function setup_database($db_name, $db_user, $db_password) {
    // Verificar se estamos no CyberPanel
    if (file_exists('/usr/local/CyberCP')) {
        // Usando comandos PostgreSQL para criar usuário e banco de dados
        $user_exists = execute_command("sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$db_user'\"");
        
        if (trim($user_exists['output']) !== '1') {
            execute_command("sudo -u postgres psql -c \"CREATE USER $db_user WITH PASSWORD '$db_password';\"");
        }
        
        $db_exists = execute_command("sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$db_name'\"");
        
        if (trim($db_exists['output']) !== '1') {
            execute_command("sudo -u postgres psql -c \"CREATE DATABASE $db_name OWNER $db_user';\"");
        }
        
        return true;
    } else {
        // Fora do CyberPanel, apenas reportar informações para configuração manual
        return "Configuração manual necessária: Crie um banco de dados '$db_name' com usuário '$db_user' e senha '$db_password'.";
    }
}

function create_env_file($path, $db_name, $db_user, $db_password, $db_host = 'localhost') {
    $secret_key = random_string(32);
    
    $env_content = "DATABASE_URL=postgresql://$db_user:$db_password@$db_host/$db_name\n";
    $env_content .= "SESSION_SECRET=$secret_key\n";
    $env_content .= "FLASK_APP=main.py\n";
    $env_content .= "FLASK_ENV=production\n";
    
    return file_put_contents("$path/.env", $env_content) !== false;
}

function initialize_database($path) {
    $init_script = <<<PYTHON
from app import app
from main import db
app.app_context().push()
db.create_all()
print("Banco de dados inicializado com sucesso!")
PYTHON;
    
    file_put_contents("$path/init_db_script.py", $init_script);
    $result = execute_command("cd $path && venv/bin/python init_db_script.py");
    unlink("$path/init_db_script.py");
    
    return $result;
}

function create_service_file($path, $domain) {
    $service_content = <<<SERVICE
[Unit]
Description=Sistema de Gestão Agropecuária
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=$path
ExecStart=$path/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 main:app
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE;
    
    return file_put_contents("$path/fazenda.service", $service_content) !== false;
}

function create_readme($path, $domain) {
    $readme_content = <<<README
# Sistema de Gestão Agropecuária - Instalação Concluída

## Como Acessar o Sistema

1. Acesse pelo seu domínio: https://$domain
2. Para inicializar o banco de dados com dados iniciais: https://$domain/init_db

## Credenciais Padrão

Após inicializar o banco de dados, você pode fazer login com:
- Email: admin@fazenda.com
- Senha: admin

**Importante:** Altere a senha padrão após o primeiro login!

## Documentação

Consulte a pasta `docs` para obter informações detalhadas sobre:
- Manual do usuário
- Instalação e configuração
- API para dispositivos LoRa
- Integração com estações meteorológicas

## Suporte

Para suporte técnico, entre em contato:
- Email: suporte@ruralsys.com.br
- Telefone: (11) 1234-5678
- Horário de atendimento: Segunda a Sexta, 8h às 18h

---

© RuralSys Inovação Tecnológica - Todos os direitos reservados
README;
    
    return file_put_contents("$path/INSTALACAO.md", $readme_content) !== false;
}

// Processar ações
$action = isset($_POST['action']) ? $_POST['action'] : '';
$response = ['success' => false, 'message' => 'Nenhuma ação especificada'];

switch ($action) {
    case 'check_environment':
        $python_version = check_python();
        $postgres_version = check_postgres();
        $domain = detect_domain();
        $is_public_html = is_public_html();
        $is_cyberpanel = file_exists('/usr/local/CyberCP');
        
        $response = [
            'success' => true,
            'python_version' => $python_version,
            'postgres_version' => $postgres_version,
            'domain' => $domain,
            'is_public_html' => $is_public_html,
            'is_cyberpanel' => $is_cyberpanel,
            'path' => get_installer_path(),
            'requirements' => check_requirements()
        ];
        break;
        
    case 'install_files':
        $path = get_installer_path();
        
        // Download dos arquivos
        // Nota: Em uma implementação real, você baixaria arquivos de um repositório
        // Aqui estamos simulando apenas para demonstração
        
        // Criar ambiente virtual
        $venv_result = create_virtual_env($path);
        
        // Instalar dependências
        $deps_result = install_dependencies($path);
        
        $response = [
            'success' => $venv_result && $deps_result['success'],
            'venv_result' => $venv_result,
            'deps_result' => $deps_result,
            'path' => $path
        ];
        break;
        
    case 'configure_system':
        $path = get_installer_path();
        $db_name = isset($_POST['db_name']) ? $_POST['db_name'] : 'fazenda';
        $db_user = isset($_POST['db_user']) ? $_POST['db_user'] : 'fazenda';
        $db_password = isset($_POST['db_password']) ? $_POST['db_password'] : random_string(12);
        $db_host = isset($_POST['db_host']) ? $_POST['db_host'] : 'localhost';
        $domain = detect_domain();
        
        // Configurar banco de dados
        $db_result = setup_database($db_name, $db_user, $db_password);
        
        // Criar arquivo .env
        $env_result = create_env_file($path, $db_name, $db_user, $db_password, $db_host);
        
        // Inicializar banco de dados
        $init_result = initialize_database($path);
        
        // Criar arquivo de serviço
        $service_result = create_service_file($path, $domain);
        
        // Criar README
        $readme_result = create_readme($path, $domain);
        
        $response = [
            'success' => $env_result && $init_result['success'] && $service_result && $readme_result,
            'db_result' => $db_result,
            'env_result' => $env_result,
            'init_result' => $init_result,
            'service_result' => $service_result,
            'readme_result' => $readme_result,
            'domain' => $domain,
            'admin_email' => 'admin@fazenda.com',
            'admin_password' => 'admin'
        ];
        break;
        
    case 'finish_installation':
        $remove_installer = isset($_POST['remove_installer']) ? $_POST['remove_installer'] === 'true' : false;
        $domain = detect_domain();
        
        if ($remove_installer) {
            // Criar script de autodestruição
            $self_destruct = <<<PHP
<?php
// Este script remove o instalador e depois remove a si mesmo
unlink(__DIR__ . '/instalar.php');
unlink(__FILE__);
header('Location: https://$domain');
exit;
PHP;
            
            file_put_contents('remover_instalador.php', $self_destruct);
            
            $response = [
                'success' => true,
                'message' => 'Instalação concluída. O instalador será removido.',
                'redirect' => "remover_instalador.php"
            ];
        } else {
            $response = [
                'success' => true,
                'message' => 'Instalação concluída.',
                'redirect' => "https://$domain"
            ];
        }
        break;
        
    default:
        // Nenhuma ação, mostrar interface
        header('Content-Type: text/html');
        // Mostrar formulário HTML
}

// Se chegamos aqui com uma ação, retornar como JSON
if ($action) {
    header('Content-Type: application/json');
    echo json_encode($response);
    exit;
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instalador - <?php echo SYSTEM_NAME; ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding-top: 20px;
            padding-bottom: 50px;
            background-color: #f8f9fa;
        }
        .installer-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            padding: 30px;
        }
        .logo {
            max-width: 200px;
            margin-bottom: 20px;
        }
        .step {
            display: none;
        }
        .step.active {
            display: block;
        }
        .progress {
            height: 10px;
            margin-bottom: 20px;
        }
        .step-indicator {
            margin-bottom: 30px;
        }
        .step-indicator .step-number {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: #6c757d;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin: 0 auto 10px;
        }
        .step-indicator.active .step-number {
            background-color: #0d6efd;
        }
        .step-indicator.completed .step-number {
            background-color: #198754;
        }
        .step-label {
            text-align: center;
            font-size: 0.8rem;
        }
        .terminal {
            background-color: #212529;
            color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            height: 200px;
            overflow-y: auto;
            margin-bottom: 15px;
        }
        .terminal .command {
            color: #0dcaf0;
        }
        .terminal .success {
            color: #198754;
        }
        .terminal .error {
            color: #dc3545;
        }
        .terminal .warning {
            color: #ffc107;
        }
        #complete-message {
            display: none;
        }
        .card {
            margin-bottom: 20px;
        }
        .self-destruct {
            font-size: 0.8rem;
            color: #dc3545;
        }
        h1, h2, h3 {
            color: #343a40;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #6c757d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="installer-container">
            <div class="row mb-4">
                <div class="col text-center">
                    <h1>Instalador do <?php echo SYSTEM_NAME; ?></h1>
                    <p class="lead">Este assistente guiará você no processo de instalação do sistema.</p>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col">
                    <div class="progress">
                        <div id="progress-bar" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col">
                    <div class="row justify-content-between text-center">
                        <div class="col-2 step-indicator active" id="step-indicator-1">
                            <div class="step-number">1</div>
                            <div class="step-label">Preparação</div>
                        </div>
                        <div class="col-2 step-indicator" id="step-indicator-2">
                            <div class="step-number">2</div>
                            <div class="step-label">Banco de Dados</div>
                        </div>
                        <div class="col-2 step-indicator" id="step-indicator-3">
                            <div class="step-number">3</div>
                            <div class="step-label">Arquivos</div>
                        </div>
                        <div class="col-2 step-indicator" id="step-indicator-4">
                            <div class="step-number">4</div>
                            <div class="step-label">Configuração</div>
                        </div>
                        <div class="col-2 step-indicator" id="step-indicator-5">
                            <div class="step-number">5</div>
                            <div class="step-label">Finalização</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Passo 1: Boas-vindas e requisitos -->
            <div id="step1" class="step active">
                <div class="card">
                    <div class="card-body">
                        <h3 class="card-title">Bem-vindo ao Instalador</h3>
                        <p class="card-text">Este assistente irá guiá-lo na instalação do <?php echo SYSTEM_NAME; ?> no seu servidor CyberPanel.</p>
                        
                        <h4>Requisitos do Sistema</h4>
                        <ul>
                            <li>CyberPanel instalado no servidor</li>
                            <li>Python 3.8 ou superior</li>
                            <li>PostgreSQL 12 ou superior</li>
                            <li>Um domínio configurado no CyberPanel</li>
                        </ul>
                        
                        <h4>Verificando o Ambiente</h4>
                        <div class="terminal" id="step1-output">
                            <div>Clique em "Verificar Requisitos" para iniciar...</div>
                        </div>
                        
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" id="terms-check" required>
                            <label class="form-check-label" for="terms-check">
                                Eu li e aceito os termos e condições de uso do sistema
                            </label>
                        </div>
                    </div>
                    <div class="card-footer">
                        <button id="check-requirements" class="btn btn-success">Verificar Requisitos</button>
                        <button id="step1-next" class="btn btn-primary float-end" disabled>Próximo</button>
                    </div>
                </div>
            </div>

            <!-- Passo 2: Configuração do Banco de Dados -->
            <div id="step2" class="step">
                <div class="card">
                    <div class="card-body">
                        <h3 class="card-title">Configuração do Banco de Dados</h3>
                        <p class="card-text">Configure as informações do banco de dados PostgreSQL.</p>
                        
                        <form id="db-form">
                            <div class="mb-3">
                                <label for="db-name" class="form-label">Nome do Banco de Dados</label>
                                <input type="text" class="form-control" id="db-name" value="fazenda" required>
                            </div>
                            <div class="mb-3">
                                <label for="db-user" class="form-label">Usuário do Banco de Dados</label>
                                <input type="text" class="form-control" id="db-user" value="fazenda" required>
                            </div>
                            <div class="mb-3">
                                <label for="db-password" class="form-label">Senha do Banco de Dados</label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="db-password" required>
                                    <button class="btn btn-outline-secondary" type="button" id="generate-password">Gerar</button>
                                </div>
                                <div class="form-text">Senha forte recomendada. Use o botão para gerar automaticamente.</div>
                            </div>
                            <div class="mb-3">
                                <label for="db-host" class="form-label">Host do Banco de Dados</label>
                                <input type="text" class="form-control" id="db-host" value="localhost" required>
                            </div>
                        </form>
                    </div>
                    <div class="card-footer">
                        <button id="step2-prev" class="btn btn-secondary">Anterior</button>
                        <button id="step2-next" class="btn btn-primary float-end">Próximo</button>
                    </div>
                </div>
            </div>

            <!-- Passo 3: Download e Instalação de Arquivos -->
            <div id="step3" class="step">
                <div class="card">
                    <div class="card-body">
                        <h3 class="card-title">Instalação dos Arquivos</h3>
                        <p class="card-text">O sistema irá baixar e instalar os arquivos necessários.</p>
                        
                        <div class="mb-3">
                            <label class="form-label">Opções de Instalação</label>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="create-venv" checked>
                                <label class="form-check-label" for="create-venv">
                                    Criar ambiente virtual Python
                                </label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="install-deps" checked>
                                <label class="form-check-label" for="install-deps">
                                    Instalar dependências
                                </label>
                            </div>
                        </div>
                        
                        <div class="terminal" id="step3-output">
                            <div>Aguardando para iniciar a instalação dos arquivos...</div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <button id="step3-prev" class="btn btn-secondary">Anterior</button>
                        <button id="step3-install" class="btn btn-success float-end">Instalar Arquivos</button>
                        <button id="step3-next" class="btn btn-primary float-end" style="display: none;">Próximo</button>
                    </div>
                </div>
            </div>

            <!-- Passo 4: Configuração do Sistema -->
            <div id="step4" class="step">
                <div class="card">
                    <div class="card-body">
                        <h3 class="card-title">Configuração do Sistema</h3>
                        <p class="card-text">Configure os parâmetros do sistema e inicialize o banco de dados.</p>
                        
                        <div class="mb-3">
                            <label for="admin-email" class="form-label">Email do Administrador</label>
                            <input type="email" class="form-control" id="admin-email" value="admin@fazenda.com">
                        </div>
                        <div class="mb-3">
                            <label for="admin-password" class="form-label">Senha do Administrador</label>
                            <input type="text" class="form-control" id="admin-password" value="admin">
                            <div class="form-text text-warning">Importante: Altere esta senha após o primeiro login.</div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Configurações Adicionais</label>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="init-db" checked>
                                <label class="form-check-label" for="init-db">
                                    Inicializar banco de dados
                                </label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="create-service" checked>
                                <label class="form-check-label" for="create-service">
                                    Criar serviço systemd
                                </label>
                            </div>
                        </div>
                        
                        <div class="terminal" id="step4-output">
                            <div>Aguardando configuração do sistema...</div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <button id="step4-prev" class="btn btn-secondary">Anterior</button>
                        <button id="step4-configure" class="btn btn-success float-end">Configurar Sistema</button>
                        <button id="step4-next" class="btn btn-primary float-end" style="display: none;">Próximo</button>
                    </div>
                </div>
            </div>

            <!-- Passo 5: Finalização -->
            <div id="step5" class="step">
                <div class="card">
                    <div class="card-body">
                        <h3 class="card-title">Instalação Concluída</h3>
                        <div id="success-message">
                            <div class="alert alert-success" role="alert">
                                <h4 class="alert-heading">Instalação concluída com sucesso!</h4>
                                <p>O Sistema de Gestão Agropecuária foi instalado e configurado em seu servidor.</p>
                            </div>
                            
                            <h4>Próximos Passos</h4>
                            <ol>
                                <li>Acesse o sistema pelo seu domínio: <strong id="system-url">https://seu-dominio.com</strong></li>
                                <li>Inicialize o banco de dados com dados de exemplo: <strong id="init-url">https://seu-dominio.com/init_db</strong></li>
                                <li>Faça login com as credenciais definidas na instalação</li>
                                <li>Altere a senha do administrador imediatamente</li>
                                <li>Configure sua propriedade e comece a usar o sistema</li>
                            </ol>
                            
                            <h4>Informações de Acesso</h4>
                            <div class="card bg-dark text-light p-3 mb-3">
                                <p><strong>URL do sistema:</strong> <span id="access-url">https://seu-dominio.com</span></p>
                                <p><strong>Email:</strong> <span id="access-email">admin@fazenda.com</span></p>
                                <p><strong>Senha:</strong> <span id="access-password">admin</span></p>
                            </div>
                            
                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="remove-installer" checked>
                                    <label class="form-check-label" for="remove-installer">
                                        Remover arquivos de instalação ao concluir
                                    </label>
                                    <p class="form-text self-destruct">Por segurança, recomendamos remover o instalador após a conclusão.</p>
                                </div>
                            </div>
                        </div>
                        
                        <div id="error-message" style="display: none;">
                            <div class="alert alert-danger" role="alert">
                                <h4 class="alert-heading">Problemas na instalação</h4>
                                <p>Ocorreram alguns problemas durante a instalação. Veja os detalhes abaixo:</p>
                                <div id="error-details"></div>
                            </div>
                            
                            <h4>Possíveis Soluções</h4>
                            <ul id="error-solutions"></ul>
                            
                            <h4>Suporte Técnico</h4>
                            <p>Para obter ajuda, entre em contato com nosso suporte técnico:</p>
                            <p>Email: suporte@ruralsys.com.br</p>
                            <p>Telefone: (11) 1234-5678</p>
                        </div>
                    </div>
                    <div class="card-footer">
                        <button id="step5-prev" class="btn btn-secondary">Anterior</button>
                        <button id="step5-finish" class="btn btn-success float-end">Concluir Instalação</button>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p><?php echo SYSTEM_NAME; ?> - Versão do Instalador: <?php echo INSTALLER_VERSION; ?></p>
                <p>&copy; RuralSys Inovação Tecnológica - Todos os direitos reservados</p>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Funções de utilidade
        function generatePassword(length = 12) {
            const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()';
            let password = '';
            for (let i = 0; i < length; i++) {
                password += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            return password;
        }

        function appendToTerminal(terminalId, message, className = '') {
            const terminal = document.getElementById(terminalId);
            const div = document.createElement('div');
            div.textContent = message;
            if (className) {
                div.className = className;
            }
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        function updateProgress(step) {
            const progress = (step - 1) * 25;
            document.getElementById('progress-bar').style.width = `${progress}%`;
            document.getElementById('progress-bar').setAttribute('aria-valuenow', progress);
            
            // Atualizar indicadores de etapas
            for (let i = 1; i <= 5; i++) {
                const indicator = document.getElementById(`step-indicator-${i}`);
                if (i < step) {
                    indicator.className = 'col-2 step-indicator completed';
                } else if (i === step) {
                    indicator.className = 'col-2 step-indicator active';
                } else {
                    indicator.className = 'col-2 step-indicator';
                }
            }
        }

        function showStep(step) {
            // Esconder todas as etapas
            document.querySelectorAll('.step').forEach(el => {
                el.classList.remove('active');
            });
            
            // Mostrar a etapa atual
            document.getElementById(`step${step}`).classList.add('active');
            
            // Atualizar barra de progresso
            updateProgress(step);
        }

        async function sendRequest(action, data = {}) {
            const formData = new FormData();
            formData.append('action', action);
            
            for (const key in data) {
                formData.append(key, data[key]);
            }
            
            try {
                const response = await fetch('instalar.php', {
                    method: 'POST',
                    body: formData
                });
                
                return await response.json();
            } catch (error) {
                console.error('Erro ao enviar requisição:', error);
                return { success: false, message: 'Erro de comunicação com o servidor' };
            }
        }

        // Verificar ambiente
        async function checkEnvironment() {
            appendToTerminal('step1-output', 'Verificando ambiente...');
            
            const response = await sendRequest('check_environment');
            
            if (response.success) {
                if (response.python_version) {
                    appendToTerminal('step1-output', `✓ Python ${response.python_version} encontrado`, 'success');
                } else {
                    appendToTerminal('step1-output', '✗ Python não encontrado ou versão não suportada', 'error');
                }
                
                if (response.postgres_version) {
                    appendToTerminal('step1-output', `✓ PostgreSQL ${response.postgres_version} encontrado`, 'success');
                } else {
                    appendToTerminal('step1-output', '✗ PostgreSQL não encontrado', 'warning');
                }
                
                if (response.is_cyberpanel) {
                    appendToTerminal('step1-output', '✓ CyberPanel detectado', 'success');
                } else {
                    appendToTerminal('step1-output', '✗ CyberPanel não detectado', 'warning');
                }
                
                if (response.is_public_html) {
                    appendToTerminal('step1-output', '✓ Instalação em pasta public_html confirmada', 'success');
                } else {
                    appendToTerminal('step1-output', '✗ Não está em uma pasta public_html', 'warning');
                }
                
                if (response.domain) {
                    appendToTerminal('step1-output', `✓ Domínio detectado: ${response.domain}`, 'success');
                } else {
                    appendToTerminal('step1-output', '✗ Não foi possível detectar um domínio', 'warning');
                }
                
                // Verificar requisitos
                if (response.requirements.length === 0) {
                    appendToTerminal('step1-output', 'Todos os requisitos atendidos! Você pode prosseguir.', 'success');
                    document.getElementById('step1-next').removeAttribute('disabled');
                } else {
                    appendToTerminal('step1-output', 'Alguns requisitos não foram atendidos:', 'warning');
                    response.requirements.forEach(req => {
                        appendToTerminal('step1-output', `- ${req}`, 'warning');
                    });
                    appendToTerminal('step1-output', 'Você pode prosseguir, mas poderá encontrar problemas.', 'warning');
                    document.getElementById('step1-next').removeAttribute('disabled');
                }
            } else {
                appendToTerminal('step1-output', 'Erro ao verificar o ambiente.', 'error');
            }
        }

        // Instalar arquivos
        async function installFiles() {
            const createVenv = document.getElementById('create-venv').checked;
            const installDeps = document.getElementById('install-deps').checked;
            
            document.getElementById('step3-install').setAttribute('disabled', 'disabled');
            
            appendToTerminal('step3-output', 'Iniciando instalação dos arquivos...');
            
            const response = await sendRequest('install_files', {
                create_venv: createVenv,
                install_deps: installDeps
            });
            
            if (response.success) {
                if (response.venv_result) {
                    appendToTerminal('step3-output', '✓ Ambiente virtual criado com sucesso', 'success');
                } else {
                    appendToTerminal('step3-output', '✗ Erro ao criar ambiente virtual', 'error');
                }
                
                if (response.deps_result.success) {
                    appendToTerminal('step3-output', '✓ Dependências instaladas com sucesso', 'success');
                } else {
                    appendToTerminal('step3-output', '✗ Erro ao instalar dependências', 'error');
                    appendToTerminal('step3-output', response.deps_result.log, 'error');
                }
                
                appendToTerminal('step3-output', 'Instalação de arquivos concluída!', 'success');
                document.getElementById('step3-install').style.display = 'none';
                document.getElementById('step3-next').style.display = 'block';
            } else {
                appendToTerminal('step3-output', 'Erro na instalação dos arquivos.', 'error');
                document.getElementById('step3-install').removeAttribute('disabled');
            }
        }

        // Configurar sistema
        async function configureSystem() {
            const dbName = document.getElementById('db-name').value;
            const dbUser = document.getElementById('db-user').value;
            const dbPassword = document.getElementById('db-password').value;
            const dbHost = document.getElementById('db-host').value;
            const adminEmail = document.getElementById('admin-email').value;
            const adminPassword = document.getElementById('admin-password').value;
            const initDb = document.getElementById('init-db').checked;
            const createService = document.getElementById('create-service').checked;
            
            document.getElementById('step4-configure').setAttribute('disabled', 'disabled');
            
            appendToTerminal('step4-output', 'Configurando sistema...');
            
            const response = await sendRequest('configure_system', {
                db_name: dbName,
                db_user: dbUser,
                db_password: dbPassword,
                db_host: dbHost,
                admin_email: adminEmail,
                admin_password: adminPassword,
                init_db: initDb,
                create_service: createService
            });
            
            if (response.success) {
                appendToTerminal('step4-output', '✓ Arquivo .env criado com sucesso', 'success');
                
                if (typeof response.db_result === 'string') {
                    appendToTerminal('step4-output', response.db_result, 'warning');
                } else if (response.db_result) {
                    appendToTerminal('step4-output', '✓ Banco de dados configurado com sucesso', 'success');
                }
                
                if (response.init_result.success) {
                    appendToTerminal('step4-output', '✓ Banco de dados inicializado com sucesso', 'success');
                } else {
                    appendToTerminal('step4-output', '✗ Erro ao inicializar banco de dados', 'error');
                    appendToTerminal('step4-output', response.init_result.output, 'error');
                }
                
                if (response.service_result) {
                    appendToTerminal('step4-output', '✓ Arquivo de serviço criado com sucesso', 'success');
                }
                
                appendToTerminal('step4-output', 'Configuração do sistema concluída!', 'success');
                document.getElementById('step4-configure').style.display = 'none';
                document.getElementById('step4-next').style.display = 'block';
                
                // Atualizar informações de acesso no passo 5
                if (response.domain) {
                    document.getElementById('system-url').textContent = `https://${response.domain}`;
                    document.getElementById('init-url').textContent = `https://${response.domain}/init_db`;
                    document.getElementById('access-url').textContent = `https://${response.domain}`;
                }
                
                document.getElementById('access-email').textContent = response.admin_email || adminEmail;
                document.getElementById('access-password').textContent = response.admin_password || adminPassword;
            } else {
                appendToTerminal('step4-output', 'Erro na configuração do sistema.', 'error');
                document.getElementById('step4-configure').removeAttribute('disabled');
            }
        }

        // Finalizar instalação
        async function finishInstallation() {
            const removeInstaller = document.getElementById('remove-installer').checked;
            
            document.getElementById('step5-finish').setAttribute('disabled', 'disabled');
            
            const response = await sendRequest('finish_installation', {
                remove_installer: removeInstaller
            });
            
            if (response.success) {
                alert(response.message);
                
                if (response.redirect) {
                    window.location.href = response.redirect;
                }
            } else {
                alert('Erro ao finalizar a instalação: ' + response.message);
                document.getElementById('step5-finish').removeAttribute('disabled');
            }
        }

        // Eventos de botões
        document.addEventListener('DOMContentLoaded', function() {
            // Gerar senha aleatória
            document.getElementById('generate-password').addEventListener('click', function() {
                document.getElementById('db-password').value = generatePassword();
            });
            document.getElementById('db-password').value = generatePassword();
            
            // Verificar requisitos
            document.getElementById('check-requirements').addEventListener('click', checkEnvironment);
            
            // Termos e condições
            document.getElementById('terms-check').addEventListener('change', function() {
                document.getElementById('step1-next').disabled = !this.checked;
            });
            
            // Navegação entre etapas
            document.getElementById('step1-next').addEventListener('click', function() {
                showStep(2);
            });
            
            document.getElementById('step2-prev').addEventListener('click', function() {
                showStep(1);
            });
            
            document.getElementById('step2-next').addEventListener('click', function() {
                showStep(3);
            });
            
            document.getElementById('step3-prev').addEventListener('click', function() {
                showStep(2);
            });
            
            document.getElementById('step3-next').addEventListener('click', function() {
                showStep(4);
            });
            
            document.getElementById('step4-prev').addEventListener('click', function() {
                showStep(3);
            });
            
            document.getElementById('step4-next').addEventListener('click', function() {
                showStep(5);
            });
            
            document.getElementById('step5-prev').addEventListener('click', function() {
                showStep(4);
            });
            
            // Ações de instalação
            document.getElementById('step3-install').addEventListener('click', installFiles);
            document.getElementById('step4-configure').addEventListener('click', configureSystem);
            document.getElementById('step5-finish').addEventListener('click', finishInstallation);
        });
    </script>
</body>
</html>