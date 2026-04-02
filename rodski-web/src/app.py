"""RodSki Web - 测试用例管理 Web 应用"""
import os
import sys

# 将项目根目录添加到 Python 路径
# app.py is in src/, project root is parent of src/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)  # 切换到项目根目录以便正确加载 config.yaml

import yaml
from flask import Flask, render_template, jsonify, request, session

# 加载配置
with open('config.yaml') as f:
    CONFIG = yaml.safe_load(f)

app = Flask(__name__, template_folder=os.path.join(project_root, 'templates'), static_folder=os.path.join(project_root, 'static'))
app.secret_key = os.urandom(24)
app.config['RODSKI_CONFIG'] = CONFIG


def get_current_project():
    """获取当前项目配置"""
    current_name = session.get('current_project', CONFIG.get('current_project', CONFIG['projects'][0]['name']))
    for proj in CONFIG['projects']:
        if proj['name'] == current_name:
            return proj
    return CONFIG['projects'][0]


def get_data_path():
    """获取当前项目的数据路径"""
    return get_current_project()['path']


# 注册蓝图
from src.api import cases, models, results, runner
app.register_blueprint(cases.bp)
app.register_blueprint(models.bp)
app.register_blueprint(results.bp)
app.register_blueprint(runner.bp)


@app.route('/')
def index():
    """首页"""
    current_proj = get_current_project()
    return render_template('index.html', current_project=current_proj, projects=CONFIG['projects'])


@app.route('/cases')
def cases_page():
    """用例管理页面"""
    current_proj = get_current_project()
    return render_template('cases.html', current_project=current_proj, projects=CONFIG['projects'])


@app.route('/models')
def models_page():
    """模型管理页面"""
    current_proj = get_current_project()
    return render_template('models.html', current_project=current_proj, projects=CONFIG['projects'])


@app.route('/results')
def results_page():
    """结果管理页面"""
    current_proj = get_current_project()
    return render_template('results.html', current_project=current_proj, projects=CONFIG['projects'])


@app.route('/runner')
def runner_page():
    """执行器页面"""
    current_proj = get_current_project()
    return render_template('runner.html', current_project=current_proj, projects=CONFIG['projects'])


@app.route('/api/projects', methods=['GET'])
def list_projects():
    """获取所有项目列表"""
    current_name = session.get('current_project', CONFIG.get('current_project', CONFIG['projects'][0]['name']))
    return jsonify({
        'projects': CONFIG['projects'],
        'current_project': current_name
    })


@app.route('/api/projects/switch', methods=['POST'])
def switch_project():
    """切换当前项目"""
    data = request.get_json()
    project_name = data.get('project_name')
    
    # 验证项目是否存在
    target = None
    for proj in CONFIG['projects']:
        if proj['name'] == project_name:
            target = proj
            break
    
    if not target:
        return jsonify({'error': f'项目不存在: {project_name}'}), 404
    
    session['current_project'] = project_name
    return jsonify({'success': True, 'current_project': project_name, 'data_path': target['path']})


@app.route('/api/current-project', methods=['GET'])
def current_project_info():
    """获取当前项目信息"""
    current_proj = get_current_project()
    return jsonify({
        'name': current_proj['name'],
        'path': current_proj['path']
    })


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'rodski-web'})


if __name__ == '__main__':
    server_config = CONFIG.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', True)
    
    # 获取当前项目（不依赖 session，只在启动时使用默认项目）
    default_project = CONFIG['projects'][0]
    current_proj_name = CONFIG.get('current_project', default_project['name'])
    current_proj = next((p for p in CONFIG['projects'] if p['name'] == current_proj_name), default_project)
    
    print(f"🚀 RodSki Web 启动中...")
    print(f"   地址: http://{host}:{port}")
    print(f"   当前项目: {current_proj['name']}")
    print(f"   数据路径: {current_proj['path']}")
    
    app.run(host=host, port=port, debug=debug)
