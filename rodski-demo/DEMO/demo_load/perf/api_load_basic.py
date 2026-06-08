# ============================================================
# RodSki LoadCompiler — plan_id: api_load_basic
# Generated: 2026-06-08 00:35:36 UTC
# Run: locust -f <this_file> --host http://localhost --users 5 --run-time 30s
# ============================================================
import random as _random
from datetime import datetime as _datetime
from locust import FastHttpUser, task, between

# --- module-level constants (inlined literals) ---
_TC_TC_LOAD_001_STEP0_METHOD = 'POST'
_TC_TC_LOAD_001_STEP0_URL = 'http://localhost:8000/api/login'
_TC_TC_LOAD_002_STEP0_METHOD = 'GET'
_TC_TC_LOAD_002_STEP0_URL = 'http://localhost:8000/api/orders'

class CompiledRodskiUser(FastHttpUser):
    host = 'http://localhost:8000'
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self._returns = []

    @task(2)
    def task_TC_LOAD_001(self):
        self._returns = []
        _resp = self.client.request(_TC_TC_LOAD_001_STEP0_METHOD, _TC_TC_LOAD_001_STEP0_URL, name='POST http://localhost:8000/api/login', json={
    'username': 'admin',
    'password': '123456'
    }, headers={})
        self._returns.append({'status_code': _resp.status_code, 'text': _resp.text})
        # step 1: verify skipped in load mode

    @task(1)
    def task_TC_LOAD_002(self):
        self._returns = []
        _resp = self.client.request(_TC_TC_LOAD_002_STEP0_METHOD, _TC_TC_LOAD_002_STEP0_URL, name='GET http://localhost:8000/api/orders', json={}, headers={})
        self._returns.append({'status_code': _resp.status_code, 'text': _resp.text})
        # step 1: verify skipped in load mode
