"""结果管理 API"""
from flask import Blueprint, jsonify, request, session
from src.services.result_service import ResultService

bp = Blueprint('results', __name__, url_prefix='/api/results')


def get_result_service():
    """获取当前项目的结果服务"""
    from src.app import CONFIG
    current_name = session.get('current_project', CONFIG.get('current_project', CONFIG['projects'][0]['name']))
    for proj in CONFIG['projects']:
        if proj['name'] == current_name:
            return ResultService(proj['path'])
    return ResultService(CONFIG['projects'][0]['path'])


@bp.route('/', methods=['GET'])
def list_results():
    """获取测试结果列表"""
    service = get_result_service()
    results = service.list_results()
    return jsonify({'results': results, 'count': len(results)})


@bp.route('/summary', methods=['GET'])
def get_summary():
    """获取测试结果汇总"""
    service = get_result_service()
    summary = service.get_statistics()
    return jsonify(summary)


@bp.route('/<path:result_dir>', methods=['GET'])
def get_result(result_dir):
    """获取单个测试结果详情"""
    service = get_result_service()
    result = service.get_result(result_dir)
    if result:
        return jsonify(result)
    return jsonify({'error': '结果不存在'}), 404
