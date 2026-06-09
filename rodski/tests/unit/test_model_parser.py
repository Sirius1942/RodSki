"""ModelParser 平台感知 location 过滤单元测试（WI-48）

覆盖 ModelParser.select_locations 的平台过滤与 priority 排序逻辑：
    - platform 专用定位器仅在匹配平台保留
    - platform=None（通用）定位器在任何平台保留（向后兼容）
    - 返回结果按 priority 升序排序
"""
from core.model_parser import ModelParser


def _loc(loc_type, value, priority=1, platform=None):
    return {
        'type': loc_type,
        'value': value,
        'priority': priority,
        'platform': platform,
        '_has_priority': True,
    }


class TestSelectLocationsPlatformFilter:
    """平台过滤规则"""

    def test_platform_specific_kept_on_matching_platform(self):
        """platform=android 的定位器在 current_platform=android 时保留"""
        locs = [_loc('id', 'a', platform='android')]
        result = ModelParser.select_locations(locs, 'android')
        assert len(result) == 1
        assert result[0]['value'] == 'a'

    def test_platform_specific_skipped_on_mismatching_platform(self):
        """platform=android 的定位器在 current_platform=ios 时跳过"""
        locs = [_loc('id', 'a', platform='android')]
        result = ModelParser.select_locations(locs, 'ios')
        assert result == []

    def test_platform_none_kept_on_any_platform(self):
        """platform=None（通用）的定位器在任何平台都保留（向后兼容）"""
        locs = [_loc('id', 'generic', platform=None)]
        assert len(ModelParser.select_locations(locs, 'android')) == 1
        assert len(ModelParser.select_locations(locs, 'ios')) == 1
        assert len(ModelParser.select_locations(locs, None)) == 1

    def test_mixed_platform_and_generic(self):
        """混合通用 + 平台专用：android 平台保留通用 + android 专用，跳过 ios 专用"""
        locs = [
            _loc('id', 'generic', priority=1, platform=None),
            _loc('id', 'android_only', priority=2, platform='android'),
            _loc('id', 'ios_only', priority=3, platform='ios'),
        ]
        values = [l['value'] for l in ModelParser.select_locations(locs, 'android')]
        assert values == ['generic', 'android_only']

    def test_current_platform_none_keeps_all(self):
        """current_platform=None 时不做平台过滤，平台专用定位器也保留"""
        locs = [
            _loc('id', 'generic', priority=1, platform=None),
            _loc('id', 'android_only', priority=2, platform='android'),
            _loc('id', 'ios_only', priority=3, platform='ios'),
        ]
        values = [l['value'] for l in ModelParser.select_locations(locs, None)]
        assert values == ['generic', 'android_only', 'ios_only']

    def test_empty_input_returns_empty(self):
        """空输入返回空列表"""
        assert ModelParser.select_locations([], 'android') == []
        assert ModelParser.select_locations(None, 'android') == []


class TestSelectLocationsPrioritySort:
    """priority 升序排序"""

    def test_sorted_by_priority_ascending(self):
        """返回结果按 priority 升序排序"""
        locs = [
            _loc('id', 'third', priority=3, platform=None),
            _loc('id', 'first', priority=1, platform=None),
            _loc('id', 'second', priority=2, platform=None),
        ]
        values = [l['value'] for l in ModelParser.select_locations(locs, 'android')]
        assert values == ['first', 'second', 'third']

    def test_priority_sort_after_platform_filter(self):
        """先平台过滤再按 priority 排序"""
        locs = [
            _loc('id', 'android_p3', priority=3, platform='android'),
            _loc('id', 'generic_p1', priority=1, platform=None),
            _loc('id', 'ios_p2', priority=2, platform='ios'),
            _loc('id', 'android_p2', priority=2, platform='android'),
        ]
        values = [l['value'] for l in ModelParser.select_locations(locs, 'android')]
        assert values == ['generic_p1', 'android_p2', 'android_p3']

    def test_missing_priority_defaults_to_one(self):
        """缺失 priority 字段时按默认值 1 排序"""
        locs = [
            {'type': 'id', 'value': 'no_prio', 'platform': None},
            _loc('id', 'p2', priority=2, platform=None),
        ]
        values = [l['value'] for l in ModelParser.select_locations(locs, 'android')]
        assert values == ['no_prio', 'p2']
