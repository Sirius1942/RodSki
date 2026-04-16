"""LLM Token 使用追踪器

零外部依赖，可选模块 — 没有 LLM 依赖时不报错。

用法:
    from llm.token_tracker import get_token_tracker, estimate_cost

    tracker = get_token_tracker()
    tracker.record(
        provider="claude",
        model="claude-sonnet-4-20250514",
        purpose="diagnosis",
        input_tokens=500,
        output_tokens=200,
        duration_ms=1200,
    )
    print(tracker.get_summary())
    tracker.save("token_usage.json")
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# 价格表（每 1M token 的美元价格：输入 / 输出）
# ---------------------------------------------------------------------------

PRICING: Dict[str, tuple] = {
    "claude-opus-4-6": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (0.8, 4.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
}

# 默认价格（Sonnet 级别）
_DEFAULT_PRICING = (3.0, 15.0)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """按公开价格估算单次调用费用（美元）

    Args:
        model: 模型标识符，需与 PRICING 中的 key 匹配。
               不匹配时使用 Sonnet 默认价格。
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数

    Returns:
        估算费用（USD）
    """
    prices = PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class LLMCallRecord:
    """单次 LLM 调用记录"""
    timestamp: datetime
    provider: str           # claude / openai
    model: str              # claude-sonnet-4-20250514
    purpose: str            # diagnosis / design / vision_locate
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration_ms: int
    cost_usd: float         # 按公开价格估算
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model": self.model,
            "purpose": self.purpose,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "duration_ms": self.duration_ms,
            "cost_usd": round(self.cost_usd, 6),
            "success": self.success,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

class TokenTracker:
    """LLM Token 使用追踪器"""

    def __init__(self):
        self._records: List[LLMCallRecord] = []

    def record(
        self,
        *,
        provider: str,
        model: str,
        purpose: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        success: bool = True,
        error: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        cost_usd: Optional[float] = None,
    ) -> None:
        """记录一次 LLM 调用

        cost_usd 和 total_tokens 可自动计算，无需手动提供。
        """
        total_tokens = input_tokens + output_tokens
        if cost_usd is None:
            cost_usd = estimate_cost(model, input_tokens, output_tokens)
        if timestamp is None:
            timestamp = datetime.now()

        self._records.append(LLMCallRecord(
            timestamp=timestamp,
            provider=provider,
            model=model,
            purpose=purpose,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            success=success,
            error=error,
        ))

    @property
    def records(self) -> List[LLMCallRecord]:
        """返回只读记录列表"""
        return list(self._records)

    def get_summary(self) -> Dict[str, Any]:
        """汇总报告

        Returns:
            包含 total_calls, total_tokens, total_cost_usd, by_purpose 的字典。
        """
        total_calls = len(self._records)
        total_tokens = sum(r.total_tokens for r in self._records)
        total_cost = sum(r.cost_usd for r in self._records)
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_duration = sum(r.duration_ms for r in self._records)
        success_count = sum(1 for r in self._records if r.success)

        by_purpose: Dict[str, Dict[str, Any]] = {}
        for r in self._records:
            if r.purpose not in by_purpose:
                by_purpose[r.purpose] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            bp = by_purpose[r.purpose]
            bp["calls"] += 1
            bp["tokens"] += r.total_tokens
            bp["cost"] += r.cost_usd
            bp["input_tokens"] += r.input_tokens
            bp["output_tokens"] += r.output_tokens

        # round costs in by_purpose
        for bp in by_purpose.values():
            bp["cost"] = round(bp["cost"], 6)

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "total_duration_ms": total_duration,
            "success_count": success_count,
            "error_count": total_calls - success_count,
            "by_purpose": by_purpose,
        }

    def save(self, path: str) -> None:
        """保存记录到 JSON 文件

        Args:
            path: 输出文件路径
        """
        output = {
            "summary": self.get_summary(),
            "records": [r.to_dict() for r in self._records],
        }
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(output, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def reset(self) -> None:
        """清空记录"""
        self._records.clear()


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_tracker: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    """获取全局 TokenTracker 单例"""
    global _tracker
    if _tracker is None:
        _tracker = TokenTracker()
    return _tracker
