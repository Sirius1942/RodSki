"""Dynamic step definitions for runtime step injection"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any


class TriggerPoint(Enum):
    """When to inject dynamic step"""
    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    ON_ERROR = "on_error"


@dataclass
class DynamicStep:
    """Dynamic step that can be injected at runtime"""
    id: str
    keyword: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    position: TriggerPoint = TriggerPoint.POST_STEP
    target_step_index: Optional[int] = None
    timeout: Optional[int] = None
    retry_on_fail: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'keyword': self.keyword,
            'params': self.params,
            'condition': self.condition,
            'position': self.position.value if isinstance(self.position, TriggerPoint) else self.position,
            'target_step_index': self.target_step_index,
            'timeout': self.timeout,
            'retry_on_fail': self.retry_on_fail,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DynamicStep':
        """Create from dictionary"""
        position = data.get('position', 'post_step')
        if isinstance(position, str):
            position = TriggerPoint(position)

        return cls(
            id=data['id'],
            keyword=data['keyword'],
            params=data.get('params', {}),
            condition=data.get('condition'),
            position=position,
            target_step_index=data.get('target_step_index'),
            timeout=data.get('timeout'),
            retry_on_fail=data.get('retry_on_fail', False),
            metadata=data.get('metadata', {})
        )


@dataclass
class ExecutionContext:
    """Runtime execution context"""
    variables: Dict[str, Any] = field(default_factory=dict)
    last_result: Dict[str, Any] = field(default_factory=dict)

    def get_driver_state(self) -> Dict[str, Any]:
        """Get current driver state"""
        return {
            'url': self.variables.get('current_url'),
            'title': self.variables.get('page_title'),
            'variables': self.variables
        }
