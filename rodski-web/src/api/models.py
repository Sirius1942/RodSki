"""模型管理 API"""
from flask import Blueprint, jsonify, request, session
from src.services.model_service import ModelService

bp = Blueprint('models', __name__, url_prefix='/api/models')


def get_model_service():
    """获取当前项目的模型服务"""
    from src.app import CONFIG
    current_name = session.get('current_project', CONFIG.get('current_project', CONFIG['projects'][0]['name']))
    for proj in CONFIG['projects']:
        if proj['name'] == current_name:
            return ModelService(proj['path'])
    return ModelService(CONFIG['projects'][0]['path'])


@bp.route('/modules', methods=['GET'])
def list_modules():
    """获取所有模块"""
    service = get_model_service()
    modules = service.list_modules()
    return jsonify({'modules': modules})


@bp.route('/', methods=['GET'])
def list_models():
    """获取模型列表"""
    service = get_model_service()
    module = request.args.get('module')
    keyword = request.args.get('keyword')
    
    if keyword:
        models = service.search_models(keyword)
    else:
        models = service.list_models(module)
    
    return jsonify({'models': models, 'count': len(models)})


@bp.route('/names', methods=['GET'])
def list_model_names():
    """获取所有模型名称（简单列表）"""
    service = get_model_service()
    names = service.list_all_model_names()
    return jsonify({'names': names, 'count': len(names)})


@bp.route('/<model_name>', methods=['GET'])
def get_model(model_name):
    """获取单个模型详情"""
    service = get_model_service()
    model = service.get_model(model_name)
    if model:
        return jsonify(model)
    return jsonify({'error': '模型不存在'}), 404
