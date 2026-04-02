"""测试执行 API"""
from flask import Blueprint, jsonify, request, session
from src.services.runner_service import RunnerService

bp = Blueprint('runner', __name__, url_prefix='/api/runner')


def get_runner_service():
    """获取当前项目的执行器服务"""
    from src.app import CONFIG
    current_name = session.get('current_project', CONFIG.get('current_project', CONFIG['projects'][0]['name']))
    for proj in CONFIG['projects']:
        if proj['name'] == current_name:
            return RunnerService(data_path=proj['path'])
    return RunnerService(data_path=CONFIG['projects'][0]['path'])


@bp.route('/run/<case_name>', methods=['POST'])
def run_case(case_name):
    """执行单个测试用例"""
    service = get_runner_service()
    result = service.run_case(case_name)
    return jsonify(result)


@bp.route('/run-batch', methods=['POST'])
def run_batch():
    """批量执行测试用例"""
    service = get_runner_service()
    data = request.get_json()
    case_names = data.get('cases', [])
    result = service.run_batch(case_names)
    return jsonify(result)


@bp.route('/history', methods=['GET'])
def get_history():
    """获取执行历史"""
    service = get_runner_service()
    limit = request.args.get('limit', 50, type=int)
    history = service.get_history(limit)
    return jsonify({'history': history})


@bp.route('/status', methods=['GET'])
def get_status():
    """获取执行器状态"""
    service = get_runner_service()
    return jsonify(service.get_status())
