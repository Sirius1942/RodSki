"""RuntimeCommandQueue 与步骤边界语义单元测试"""
from collections import deque

from core.runtime_control import (
    GracefulRunTermination,
    ForceRunTermination,
    RuntimeCommandQueue,
    BaseRuntimeControl,
)


class _StubExecutor:
    def __init__(self):
        self.temp_models = None
        self.temp_tables = None

    def apply_insert_resources(self, temp_models, temp_tables):
        self.temp_models = temp_models
        self.temp_tables = temp_tables


class TestRuntimeControl:
    def test_insert_extends_deque_order(self):
        rq = RuntimeCommandQueue()
        ex = _StubExecutor()
        dq = deque([{"action": "a", "model": "", "data": ""}])
        rq.insert(
            [
                {"action": "b", "model": "", "data": ""},
                {"action": "c", "model": "", "data": ""},
            ],
            temp_models={
                "M1": {
                    "e1": {
                        "type": "id",
                        "value": "x",
                        "driver_type": "web",
                        "element_type": "",
                        "interfacename": "",
                    }
                }
            },
            temp_tables={"T1": {"R1": {"f": "v"}}},
        )
        rq.drain_at_boundary(ex, dq)
        assert list(dq) == [
            {"action": "b", "model": "", "data": ""},
            {"action": "c", "model": "", "data": ""},
            {"action": "a", "model": "", "data": ""},
        ]
        assert ex.temp_models is not None and "M1" in ex.temp_models
        assert ex.temp_tables is not None and "T1" in ex.temp_tables

    def test_graceful_terminate_raises(self):
        rq = RuntimeCommandQueue()
        ex = _StubExecutor()
        dq = deque()
        rq.terminate(force=False)
        try:
            rq.drain_at_boundary(ex, dq)
            assert False, "expected GracefulRunTermination"
        except GracefulRunTermination:
            pass

    def test_force_terminate_raises(self):
        rq = RuntimeCommandQueue()
        ex = _StubExecutor()
        dq = deque()
        rq.terminate(force=True)
        try:
            rq.drain_at_boundary(ex, dq)
            assert False, "expected ForceRunTermination"
        except ForceRunTermination:
            pass

    def test_base_runtime_control_noop(self):
        base = BaseRuntimeControl()
        ex = _StubExecutor()
        dq = deque([{"action": "wait", "model": "", "data": "0"}])
        base.drain_at_boundary(ex, dq)
        assert len(dq) == 1

    def test_pause_wait_unpaused_then_resume(self):
        rq = RuntimeCommandQueue()
        ex = _StubExecutor()
        rq.pause()
        rq.drain_at_boundary(ex, deque())
        assert rq.wait_unpaused(timeout=0.01) is False
        rq.resume()
        rq.drain_at_boundary(ex, deque())
        assert rq.wait_unpaused(timeout=0.01) is True
