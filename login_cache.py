"""本地登录缓存工具。"""

import json
import os
import re
from datetime import datetime


CACHE_DIR = '.cache'
CACHE_PREFIX = 'gzhu_login_'
CACHE_SUFFIX = '.json'
PROBE_URL = 'http://jwxt.gzhu.edu.cn/sso/driot4login'


def _safe_username(username: str) -> str:
    return re.sub(r'[^0-9A-Za-z._-]', '_', username or 'default')


def _cache_path(username: str) -> str:
    return os.path.join(os.path.abspath('.'), CACHE_DIR, f'{CACHE_PREFIX}{_safe_username(username)}{CACHE_SUFFIX}')


def load_login_cache(username: str):
    """读取本地缓存的 cookie 字典，失败返回 None。"""
    path = _cache_path(username)
    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('username') != username:
            return None
        cookies = data.get('cookies', {})
        return cookies if isinstance(cookies, dict) else None
    except Exception:
        return None


def save_login_cache(username: str, session):
    """保存当前 session 的 cookie 到本地。"""
    path = _cache_path(username)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        'username': username,
        'saved_at': datetime.now().isoformat(timespec='seconds'),
        'cookies': session.cookies.get_dict(),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def login_with_cache(g):
    """优先使用本地登录缓存，失败后回退到账号密码登录。"""
    cached = load_login_cache(g.username)
    if cached:
        g.client.cookies.update(cached)
        try:
            probe = g.client.get(PROBE_URL, headers=g.base_headers, timeout=None)
            if probe is not None and probe.status_code < 400 and 'cas/login' not in probe.url.lower():
                save_login_cache(g.username, g.client)
                return True, 'cache'
        except Exception:
            pass

        # 缓存失效，清掉 cookie 再尝试账号密码登录
        g.client.cookies.clear()

    if g.login():
        save_login_cache(g.username, g.client)
        return True, 'password'

    return False, 'failed'
