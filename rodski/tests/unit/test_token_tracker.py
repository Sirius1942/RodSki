"""LLM Token 追踪器的单元测试"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from llm.token_tracker import (
    TokenTracker,
    LLMCallRecord,
    estimate_cost,
    get_token_tracker,
    PRICING,
    _DEFAULT_PRICING,
)


# ---------------------------------------------------------------------------
# estimate_cost 测试
# ---------------------------------------------------------------------------

class TestEstimateCost:
    """测试价格估算函数"""

    def test_known_model_cost(self):
        """已知模型的费用按 PRICING 表计算"""
        # claude-opus-4-6: input=15.0/1M, output=75.0/1M
        cost = estimate_cost("claude-opus-4-6", input_tokens=1000, output_tokens=500)
        expected = (1000 * 15.0 + 500 * 75.0) / 1_000_000
        assert abs(cost - expected) < 1e-9

    def test_unknown_model_uses_default(self):
        """未知模型使用默认（Sonnet）价格"""
        cost = estimate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
        expected = (1000 * _DEFAULT_PRICING[0] + 500 * _DEFAULT_PRICING[1]) / 1_000_000
        assert abs(cost - expected) < 1e-9

    def test_zero_tokens(self):
        """零 token 费用为零"""
        assert estimate_cost("gpt-4o", 0, 0) == 0.0

    def test_gpt4o_mini_cost(self):
        """gpt-4o-mini 的低价格计算"""
        cost = estimate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=1_000_000)
        expected = 0.15 + 0.6
        assert abs(cost - expected) < 1e-9

    def test_all_pricing_entries_have_two_elements(self):
        """价格表中每个条目都应有输入和输出两个值"""
        for model, prices in PRICING.items():
            assert len(prices) == 2, f"{model} should have (input, output) tuple"
            assert prices[0] >= 0
            assert prices[1] >= 0


# ---------------------------------------------------------------------------
# LLMCallRecord 测试
# ---------------------------------------------------------------------------

class TestLLMCallRecord:
    """测试 LLM 调用记录数据类"""

    def test_to_dict(self):
        """to_dict 返回可 JSON 序列化的字典"""
        ts = datetime(2026, 4, 16, 10, 0, 0)
        record = LLMCallRecord(
            timestamp=ts,
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="diagnosis",
            input_tokens=500,
            output_tokens=200,
            total_tokens=700,
            duration_ms=1200,
            cost_usd=0.0045,
            success=True,
        )
        d = record.to_dict()
        assert d["timestamp"] == "2026-04-16T10:00:00"
        assert d["provider"] == "claude"
        assert d["total_tokens"] == 700
        assert d["success"] is True
        assert d["error"] is None
        # 确保可以 JSON 序列化
        json.dumps(d)

    def test_to_dict_with_error(self):
        """带错误信息的记录能正确序列化"""
        record = LLMCallRecord(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-4o",
            purpose="vision_locate",
            input_tokens=100,
            output_tokens=0,
            total_tokens=100,
            duration_ms=500,
            cost_usd=0.0,
            success=False,
            error="rate limit exceeded",
        )
        d = record.to_dict()
        assert d["success"] is False
        assert d["error"] == "rate limit exceeded"


# ---------------------------------------------------------------------------
# TokenTracker 测试
# ---------------------------------------------------------------------------

class TestTokenTracker:
    """测试 Token 追踪器核心功能"""

    def test_empty_tracker_summary(self):
        """空追踪器返回零汇总"""
        tracker = TokenTracker()
        summary = tracker.get_summary()
        assert summary["total_calls"] == 0
        assert summary["total_tokens"] == 0
        assert summary["total_cost_usd"] == 0.0
        assert summary["by_purpose"] == {}

    def test_record_single_call(self):
        """记录单次调用后汇总正确"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="diagnosis",
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2000,
        )
        summary = tracker.get_summary()
        assert summary["total_calls"] == 1
        assert summary["total_tokens"] == 1500
        assert summary["total_input_tokens"] == 1000
        assert summary["total_output_tokens"] == 500
        assert summary["success_count"] == 1
        assert summary["error_count"] == 0
        assert "diagnosis" in summary["by_purpose"]
        assert summary["by_purpose"]["diagnosis"]["calls"] == 1

    def test_record_multiple_calls(self):
        """记录多次调用后汇总正确"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="diagnosis",
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2000,
        )
        tracker.record(
            provider="openai",
            model="gpt-4o",
            purpose="vision_locate",
            input_tokens=2000,
            output_tokens=300,
            duration_ms=1500,
        )
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="diagnosis",
            input_tokens=800,
            output_tokens=400,
            duration_ms=1800,
            success=False,
            error="timeout",
        )
        summary = tracker.get_summary()
        assert summary["total_calls"] == 3
        assert summary["total_tokens"] == 1500 + 2300 + 1200
        assert summary["success_count"] == 2
        assert summary["error_count"] == 1
        assert summary["by_purpose"]["diagnosis"]["calls"] == 2
        assert summary["by_purpose"]["vision_locate"]["calls"] == 1
        assert summary["total_duration_ms"] == 2000 + 1500 + 1800

    def test_auto_cost_calculation(self):
        """cost_usd 自动按 PRICING 表计算"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-opus-4-6",
            purpose="design",
            input_tokens=10000,
            output_tokens=5000,
            duration_ms=3000,
        )
        expected_cost = estimate_cost("claude-opus-4-6", 10000, 5000)
        assert tracker.records[0].cost_usd == expected_cost

    def test_manual_cost_override(self):
        """手动传入 cost_usd 时不自动计算"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="test",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
            cost_usd=0.99,
        )
        assert tracker.records[0].cost_usd == 0.99

    def test_total_tokens_auto_calculated(self):
        """total_tokens 自动为 input + output 之和"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="test",
            input_tokens=300,
            output_tokens=200,
            duration_ms=500,
        )
        assert tracker.records[0].total_tokens == 500

    def test_records_property_returns_copy(self):
        """records 属性返回副本，修改不影响内部状态"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="test",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
        )
        records = tracker.records
        records.clear()
        assert len(tracker.records) == 1

    def test_reset(self):
        """reset 清空所有记录"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="test",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
        )
        assert len(tracker.records) == 1
        tracker.reset()
        assert len(tracker.records) == 0
        assert tracker.get_summary()["total_calls"] == 0

    def test_save_to_json(self, tmp_path):
        """save 方法将记录写入 JSON 文件"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="diagnosis",
            input_tokens=500,
            output_tokens=200,
            duration_ms=1200,
        )
        tracker.record(
            provider="openai",
            model="gpt-4o",
            purpose="vision_locate",
            input_tokens=1000,
            output_tokens=100,
            duration_ms=800,
            success=False,
            error="api error",
        )

        out_path = str(tmp_path / "usage.json")
        tracker.save(out_path)

        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        assert "summary" in data
        assert "records" in data
        assert data["summary"]["total_calls"] == 2
        assert len(data["records"]) == 2
        assert data["records"][0]["provider"] == "claude"
        assert data["records"][1]["success"] is False

    def test_save_creates_parent_dirs(self, tmp_path):
        """save 自动创建不存在的父目录"""
        tracker = TokenTracker()
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="test",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
        )
        deep_path = str(tmp_path / "a" / "b" / "c" / "usage.json")
        tracker.save(deep_path)
        assert Path(deep_path).exists()

    def test_custom_timestamp(self):
        """可以传入自定义 timestamp"""
        tracker = TokenTracker()
        custom_ts = datetime(2025, 1, 1, 0, 0, 0)
        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="test",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
            timestamp=custom_ts,
        )
        assert tracker.records[0].timestamp == custom_ts


# ---------------------------------------------------------------------------
# 全局单例测试
# ---------------------------------------------------------------------------

class TestGlobalSingleton:
    """测试全局 TokenTracker 单例"""

    def test_get_token_tracker_returns_same_instance(self):
        """多次调用 get_token_tracker 返回同一实例"""
        import llm.token_tracker as mod
        # 重置全局状态
        mod._tracker = None
        t1 = get_token_tracker()
        t2 = get_token_tracker()
        assert t1 is t2
        # 清理
        mod._tracker = None

    def test_singleton_accumulates(self):
        """全局单例跨调用累积记录"""
        import llm.token_tracker as mod
        mod._tracker = None
        tracker = get_token_tracker()
        tracker.reset()

        tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="a",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
        )

        # 通过 get_token_tracker 再次获取
        same_tracker = get_token_tracker()
        same_tracker.record(
            provider="claude",
            model="claude-sonnet-4-6",
            purpose="b",
            input_tokens=200,
            output_tokens=100,
            duration_ms=600,
        )

        assert tracker.get_summary()["total_calls"] == 2
        # 清理
        mod._tracker = None
