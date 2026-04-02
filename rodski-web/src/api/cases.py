"""用例管理 API"""
from flask import Blueprint, jsonify, request, session
from src.services.case_service import CaseService

bp = Blueprint('cases', __name__, url_prefix='/api/cases')


def get_case_service():
    """获取当前项目的用例服务"""
    from src.app import CONFIG
    current_name = session.get('current_project', CONFIG.get('current_project', CONFIG['projects'][0]['name']))
    for proj in CONFIG['projects']:
        if proj['name'] == current_name:
            return CaseService(proj['path'])
    return CaseService(CONFIG['projects'][0]['path'])


@bp.route('/modules', methods=['GET'])
def list_modules():
    """获取所有模块"""
    service = get_case_service()
    modules = service.list_modules()
    return jsonify({'modules': modules})


@bp.route('/', methods=['GET'])
def list_cases():
    """获取用例列表"""
    service = get_case_service()
    module = request.args.get('module')
    keyword = request.args.get('keyword')
    
    if keyword:
        cases = service.search_cases(keyword)
    else:
        cases = service.list_cases(module)
    
    return jsonify({'cases': cases, 'count': len(cases)})


@bp.route('/<case_name>', methods=['GET'])
def get_case(case_name):
    """获取单个用例详情"""
    service = get_case_service()
    case = service.get_case(case_name)
    if case:
        return jsonify(case)
    return jsonify({'error': '用例不存在'}), 404


@bp.route('/explain/<case_name>', methods=['GET'])
def explain_case(case_name):
    """解释用例为可读文本"""
    service = get_case_service()
    explanation = service.explain_case(case_name)
    if explanation:
        return jsonify({'explanation': explanation})
    return jsonify({'error': '用例不存在'}), 404
