
"""Flask entrypoint for the enhanced reservation server."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from functools import wraps
import yaml
from flask import Flask, jsonify, render_template, request, g
from flask_cors import CORS
from flask_socketio import SocketIO, disconnect, emit

from auth import SessionManager, UserStore
from reservation_manager import ReservationManager



CN_TZ = ZoneInfo('Asia/Shanghai')
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR.parent / 'config.yaml'
COOKIES_ROOT = BASE_DIR / 'cookies_file'
COOKIE_TEMPLATE = BASE_DIR / 'getCookies.txt'
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_DB = DATA_DIR / 'users.json'


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SPORT_RESERVE_SECRET', 'dev-secret')
app.config['JSON_AS_ASCII'] = False

CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')


with CONFIG_PATH.open('r', encoding='utf-8') as fh:
    CONFIG = yaml.safe_load(fh)


user_store = UserStore(USERS_DB)
sessions = SessionManager(lifetime_minutes=60 * 12)
reservation_manager = ReservationManager(socketio, user_store, COOKIES_ROOT, COOKIE_TEMPLATE)


def _auth_token() -> Optional[str]:
    header = request.headers.get('Authorization')
    if header and header.lower().startswith('bearer '):
        return header[7:]
    return request.cookies.get('token') or request.args.get('token')


def require_auth(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any):
        token = _auth_token()
        user_id = sessions.validate(token)
        if not user_id:
            return jsonify({'error': '未登录或会话已过期'}), 401
        g.current_user_id = user_id
        g.current_token = token
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def _parse_json() -> Dict[str, Any]:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return {}


def _ensure_local(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=CN_TZ)
    return dt.astimezone(CN_TZ)


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        value_str = value.strip().lower()
        if value_str in {'1', 'true', 'yes', 'y', 'on'}:
            return True
        if value_str in {'0', 'false', 'no', 'n', 'off', ''}:
            return False
    return bool(value)


def _to_int(value: Any, default: int, minimum: int = 1) -> int:
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        candidate = default
    return max(minimum, candidate)


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.route('/')
def index() -> Any:
    return render_template(
        'index2.html',
        server_url=CONFIG['SPORT_RESERVE']['SERVER_URL'],
        port=CONFIG['SPORT_RESERVE']['PORT']
    )


@app.route('/api/register', methods=['POST'])
def register() -> Any:
    data = _parse_json()
    user_id = (data.get('userId') or '').strip()
    name = (data.get('name') or '').strip() or user_id
    password = data.get('password') or ''
    confirm = data.get('confirmPassword') or password
    if not user_id or not password:
        return jsonify({'error': '学号/工号和密码不能为空'}), 400
    if password != confirm:
        return jsonify({'error': '两次输入的密码不一致'}), 400
    try:
        user = user_store.create_user(user_id, name, password)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 409
    user_store.ensure_cookie_file(COOKIES_ROOT, COOKIE_TEMPLATE, user_id)
    return jsonify({'message': '注册成功', 'user': {'userId': user['user_id'], 'name': user['name']}})


@app.route('/api/login', methods=['POST'])
def login() -> Any:
    data = _parse_json()
    user_id = (data.get('userId') or '').strip()
    password = data.get('password') or ''
    if not user_id or not password:
        return jsonify({'error': '学号/工号和密码不能为空'}), 400
    user = user_store.verify_credentials(user_id, password)
    if not user:
        return jsonify({'error': '账号或密码错误'}), 401
    token = sessions.create_session(user_id)
    user_store.ensure_cookie_file(COOKIES_ROOT, COOKIE_TEMPLATE, user_id)
    return jsonify({
        'token': token,
        'user': {
            'userId': user['user_id'],
            'name': user['name'],
        }
    })


@app.route('/api/logout', methods=['POST'])
@require_auth
def logout() -> Any:
    token = getattr(g, 'current_token', None)
    sessions.invalidate(token)
    return jsonify({'message': '已退出登录'})


@app.route('/api/me', methods=['GET'])
@require_auth
def me() -> Any:
    user = user_store.get_user(g.current_user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'user': {'userId': user['user_id'], 'name': user['name']}})



def _validate_payload(data: Dict[str, Any]) -> Optional[str]:
    required_fields = {
        'youName': '姓名不能为空',
        'appointmentDay': '请选择预约日期',
        'appointmentTime': '请选择预约时间',
        'authAccount': '请输入统一认证账号',
        'password': '请输入统一认证密码',
    }
    for field, message in required_fields.items():
        if not (data.get(field) or '').strip():
            return message
    return None


@app.route('/api/appointments', methods=['GET'])
@require_auth
def list_appointments() -> Any:
    jobs = reservation_manager.list_jobs(g.current_user_id)
    return jsonify({'jobs': jobs})


@app.route('/api/appointments', methods=['POST'])
@require_auth

def create_appointment() -> Any:
    data = _parse_json()
    error = _validate_payload(data)
    if error:
        return jsonify({'error': error}), 400

    run_at_raw = data.get('runAt')
    run_at: Optional[datetime] = None
    if run_at_raw:
        try:
            run_at = _ensure_local(datetime.fromisoformat(run_at_raw))
        except ValueError:
            return jsonify({'error': '执行时间格式不正确，应为 ISO8601 格式'}), 400
    run_at = _ensure_local(run_at) or datetime.now(CN_TZ)

    auth_account = (data.get('authAccount') or g.current_user_id or '').strip()
    password = (data.get('password') or '').strip()
    if not auth_account:
        return jsonify({'error': '请输入统一认证账号'}), 400
    if not password:
        return jsonify({'error': '请输入统一认证密码'}), 400

    payload = {
        'you_name': data.get('youName').strip(),
        'auth_account': auth_account,
        'appointment_day': data.get('appointmentDay').strip(),
        'appointment_time_start': data.get('appointmentTime').strip(),
        'sport_type': (data.get('sportType') or '001').strip(),
        'yylx': _to_float(data.get('yylx'), 1.0),
        'target_time_str': (data.get('targetTime') or '12:30').strip(),
        'run_at': run_at.isoformat(),
        'wait_until_target': _to_bool(data.get('waitUntilTarget', False)),
        'max_attempts': _to_int(data.get('maxAttempts'), 3),
        'retry_delay': _to_int(data.get('retryDelay'), 1),
    }
    payload['password'] = password

    job = reservation_manager.schedule_job(g.current_user_id, payload)
    return jsonify({'job': job})

@app.route('/api/appointments/<job_id>', methods=['GET'])
@require_auth
def get_appointment(job_id: str) -> Any:
    job = reservation_manager.get_job(g.current_user_id, job_id)
    if not job:
        return jsonify({'error': '未找到对应的任务'}), 404
    return jsonify({'job': job})


@app.route('/api/appointments/<job_id>/cancel', methods=['POST'])
@require_auth
def cancel_appointment(job_id: str) -> Any:
    job = reservation_manager.cancel_job(g.current_user_id, job_id)
    if not job:
        return jsonify({'error': '未找到对应的任务'}), 404
    return jsonify({'job': job})


# ------------------------------------------------------------------
# Socket.IO handlers
# ------------------------------------------------------------------
@socketio.on('connect')
def socket_connect():  # type: ignore[override]
    emit('connected', {'message': 'connected'})


@socketio.on('authenticate')
def socket_authenticate(data: Dict[str, Any]):  # type: ignore[override]
    token = (data or {}).get('token')
    user_id = sessions.validate(token)
    if not user_id:
        emit('auth_error', {'error': '认证失败，token 无效'})
        disconnect()
        return
    reservation_manager.register_connection(user_id, request.sid)
    emit('auth_ok', {'userId': user_id})
    # 推送当前任务列表
    emit('job_snapshot', {'jobs': reservation_manager.list_jobs(user_id)})


@socketio.on('disconnect')
def socket_disconnect():  # type: ignore[override]
    reservation_manager.unregister_connection(request.sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=CONFIG['SPORT_RESERVE']['PORT'], allow_unsafe_werkzeug=True)

