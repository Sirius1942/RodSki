"""浏览器插件专用 API - 环境管理、失败诊断、录制上传"""
import json
import os
import time
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('plugin', __name__, url_prefix='/api/plugin')

# 失败信息内存缓存（rodski core 运行失败时写入）
_last_failure = None
# 当前激活的环境
_current_env = None
# 录制上传存储目录
_recordings_dir = None


def get_recordings_dir():
    global _recordings_dir
    if _recordings_dir is None:
        _recordings_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'recordings'
        )
        os.makedirs(_recordings_dir, exist_ok=True)
    return _recordings_dir


# ---- 环境管理 ----

@bp.route('/env/list', methods=['GET'])
def env_list():
    """获取可用环境列表"""
    # 读取 globalvalue.xml 中的 env 配置（如有）
    envs = _discover_envs()
    return jsonify({
        'ok': True,
        'envs': envs,
        'current': _current_env,
    })


@bp.route('/env/switch', methods=['POST'])
def env_switch():
    """切换当前环境"""
    global _current_env
    data = request.get_json(silent=True) or {}
    env = data.get('env', '').strip()
    if not env:
        return jsonify({'ok': False, 'error': '缺少 env 参数'}), 400
    _current_env = env
    return jsonify({'ok': True, 'env': env, 'switched_at': datetime.now().isoformat()})


@bp.route('/env/current', methods=['GET'])
def env_current():
    """获取当前环境"""
    return jsonify({'ok': True, 'env': _current_env})


def _discover_envs():
    """从 config.yaml projects 中发现环境，或返回默认列表"""
    config = current_app.config.get('RODSKI_CONFIG', {})
    projects = config.get('projects', [])
    if projects:
        # 从项目名中提取环境标记（格式如 "myapp-beta", "myapp-prod"）
        envs_from_projects = []
        for p in projects:
            name = p.get('name', '')
            for suffix in ['local', 'dev', 'beta', 'staging', 'prod', 'test', 'ci']:
                if name.endswith(f'-{suffix}') or name == suffix:
                    if suffix not in envs_from_projects:
                        envs_from_projects.append(suffix)
        if envs_from_projects:
            return envs_from_projects
    # 默认环境列表
    return ['local', 'beta', 'staging', 'prod']


# ---- 失败诊断 ----

@bp.route('/last-failure', methods=['GET'])
def last_failure():
    """获取最近一次测试失败信息（供插件高亮诊断）"""
    if _last_failure is None:
        return jsonify({'ok': False, 'failure': None, 'message': '暂无失败记录'})
    return jsonify({'ok': True, 'failure': _last_failure})


@bp.route('/report-failure', methods=['POST'])
def report_failure():
    """rodski core 执行失败后上报失败信息（内部调用）"""
    global _last_failure
    data = request.get_json(silent=True) or {}
    _last_failure = {
        'reported_at': datetime.now().isoformat(),
        'step_id': data.get('step_id'),
        'element_name': data.get('element_name'),
        'model_name': data.get('model_name'),
        'locator': data.get('locator'),  # {type, value}
        'tag': data.get('tag'),
        'error_message': data.get('error_message'),
        'url': data.get('url'),
        'screenshot_path': data.get('screenshot_path'),
    }
    return jsonify({'ok': True})


@bp.route('/clear-failure', methods=['POST'])
def clear_failure():
    """清除失败记录"""
    global _last_failure
    _last_failure = None
    return jsonify({'ok': True})


# ---- 录制上传 ----

@bp.route('/recording/upload', methods=['POST'])
def recording_upload():
    """接收浏览器插件上传的录制素材包"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'ok': False, 'error': '请求体为空或非 JSON'}), 400

    recordings_dir = get_recordings_dir()
    # 微秒 + 随机后缀，避免并发上传时文件名冲突
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    rand_suffix = uuid.uuid4().hex[:6]
    filename = f'recording_{timestamp}_{rand_suffix}.json'
    filepath = os.path.join(recordings_dir, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        return jsonify({'ok': False, 'error': f'写入失败: {e}'}), 500

    step_count = data.get('total_steps', len(data.get('steps', [])))
    screenshot_count = data.get('total_screenshots', len(data.get('screenshots', [])))

    return jsonify({
        'ok': True,
        'filename': filename,
        'path': filepath,
        'step_count': step_count,
        'screenshot_count': screenshot_count,
        'saved_at': datetime.now().isoformat(),
    })


@bp.route('/recording/list', methods=['GET'])
def recording_list():
    """列出已上传的录制文件"""
    recordings_dir = get_recordings_dir()
    files = []
    for fname in sorted(os.listdir(recordings_dir), reverse=True)[:20]:
        if fname.endswith('.json'):
            fpath = os.path.join(recordings_dir, fname)
            stat = os.stat(fpath)
            files.append({
                'filename': fname,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            })
    return jsonify({'ok': True, 'recordings': files})


@bp.route('/recording/<filename>', methods=['GET'])
def recording_get(filename):
    """获取指定录制文件内容"""
    # 安全校验：只允许 recording_*.json 文件名
    if not filename.startswith('recording_') or not filename.endswith('.json'):
        return jsonify({'ok': False, 'error': '非法文件名'}), 400
    recordings_dir = get_recordings_dir()
    filepath = os.path.join(recordings_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)
    return jsonify({'ok': True, 'data': data})
