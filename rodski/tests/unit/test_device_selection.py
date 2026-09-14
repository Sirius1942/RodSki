"""设备选择（用例执行层配置）单元测试 — DeviceCount/DeviceMix/DeviceScope/DeviceList

这一层的核心契约只有一条：**零设备是唯一的硬失败**，其余一律降级并告警。
用户的原始要求是「至少有一个模拟器或真机可以执行情况下就可以自动执行」，
下面每个降级用例都是这条要求的一个反例防线。
"""
import pytest

try:
    from rodski.core.device_scheduler import (
        Device,
        DeviceSelection,
        DeviceSelectionError,
        _apply_mix_preference,
        _device_readiness_rank,
        _split_csv,
        format_device_selection,
        is_multi_device_configured,
        load_mobile_group,
        parse_device_selection,
        resolve_explicit_devices,
        select_devices,
    )
except ImportError:
    from core.device_scheduler import (
        Device,
        DeviceSelection,
        DeviceSelectionError,
        _apply_mix_preference,
        _device_readiness_rank,
        _split_csv,
        format_device_selection,
        is_multi_device_configured,
        load_mobile_group,
        parse_device_selection,
        resolve_explicit_devices,
        select_devices,
    )


REAL = Device(udid="00008130-001979EE3CF3803A", platform="ios",
              name="Tars2", state="connected", kind="real")
SIM_BOOTED = Device(udid="015EA67B-BBBB", platform="ios",
                    name="iPhone 16 Pro", state="Booted", kind="simulator")
SIM_SHUTDOWN = Device(udid="AC199BB6-AAAA", platform="ios",
                      name="iPhone 16", state="Shutdown", kind="simulator")


class TestSplitCsv:
    def test_comma_separated(self):
        assert _split_csv("a,b,c") == ["a", "b", "c"]

    def test_dedupes_preserving_order(self):
        assert _split_csv("b,a,b") == ["b", "a"]

    def test_strips_whitespace_and_drops_blanks(self):
        assert _split_csv(" a , , b ") == ["a", "b"]

    def test_none_is_empty(self):
        assert _split_csv(None) == []


class TestParseDeviceSelection:
    def test_defaults_are_unrestrictive(self):
        """不写任何 Device* 变量 ⇒ 与 v11.2.0 逐字节相同（用上全部发现的设备）。"""
        sel = parse_device_selection({})

        assert sel.count is None
        assert sel.mix == []
        assert sel.scope == "all"
        assert sel.explicit == []
        assert sel.is_default is True

    def test_none_group_is_default(self):
        assert parse_device_selection(None).is_default is True

    def test_full_config(self):
        sel = parse_device_selection({
            "DeviceCount": "2",
            "DeviceMix": "real,simulator",
            "DeviceScope": "all",
            "DeviceList": "UDID-A,UDID-B",
        })

        assert sel.count == 2
        assert sel.mix == ["real", "simulator"]
        assert sel.explicit == ["UDID-A", "UDID-B"]
        assert sel.is_default is False

    def test_non_integer_count_means_unlimited(self):
        assert parse_device_selection({"DeviceCount": "多台"}).count is None

    @pytest.mark.parametrize("raw", ["0", "-3"])
    def test_count_below_one_clamps(self, raw):
        assert parse_device_selection({"DeviceCount": raw}).count == 1

    def test_unknown_scope_falls_back_to_all(self):
        assert parse_device_selection({"DeviceScope": "tablet"}).scope == "all"

    def test_scope_is_case_insensitive(self):
        assert parse_device_selection({"DeviceScope": "REAL"}).scope == "real"


class TestApplyMixPreference:
    def test_mix_real_first(self):
        ordered = _apply_mix_preference([SIM_BOOTED, REAL], ["real", "simulator"], "all")

        assert ordered[0] is REAL

    def test_mix_simulator_first(self):
        ordered = _apply_mix_preference([REAL, SIM_BOOTED], ["simulator", "real"], "all")

        assert ordered[0] is SIM_BOOTED

    def test_unmentioned_devices_kept_at_the_end(self):
        other = Device(udid="U3", platform="ios", name="iPhone 17", kind="simulator")
        ordered = _apply_mix_preference([SIM_BOOTED, REAL, other], ["real"], "all")

        assert ordered == [REAL, SIM_BOOTED, other]

    def test_booted_simulator_preferred_over_shutdown(self):
        """本机有 30+ 台 Shutdown 模拟器，按枚举序取前 N 台会挑到要现 boot 的那些。"""
        ordered = _apply_mix_preference([SIM_SHUTDOWN, SIM_BOOTED], ["simulator"], "all")

        assert ordered[0] is SIM_BOOTED

    def test_scope_real_filters(self):
        assert _apply_mix_preference([REAL, SIM_BOOTED], [], "real") == [REAL]

    def test_scope_simulator_filters(self):
        assert _apply_mix_preference([REAL, SIM_BOOTED], [], "simulator") == [SIM_BOOTED]

    def test_unknown_mix_value_is_ignored_not_fatal(self):
        ordered = _apply_mix_preference([REAL, SIM_BOOTED], ["tablet", "real"], "all")

        assert ordered[0] is REAL

    def test_readiness_rank_real_connected(self):
        assert _device_readiness_rank(REAL) == 0

    def test_readiness_rank_simulator_booted_vs_shutdown(self):
        assert _device_readiness_rank(SIM_BOOTED) == 0
        assert _device_readiness_rank(SIM_SHUTDOWN) == 1


class TestSelectDevices:
    def test_zero_devices_is_the_only_hard_failure(self):
        with pytest.raises(DeviceSelectionError):
            select_devices([], DeviceSelection())

    def test_default_takes_all_discovered(self):
        """不写 DeviceCount ⇒ 用上全部发现的设备（与 v11.2.0 一致）。"""
        selected, warnings = select_devices([SIM_BOOTED, REAL], DeviceSelection())

        assert selected == [REAL, SIM_BOOTED]        # 全都要，只是真机排在前面
        assert warnings == []

    def test_real_device_wins_the_last_slot_when_no_mix_is_configured(self):
        """只写 DeviceCount、没写 DeviceMix 时，真机必须占到一个名额。

        本机有 20+ 台模拟器，若按发现顺序截断，真机永远被挤出前 N 台 ——
        配置里明明有一台可用真机，实际一台都没用上。
        """
        selected, warnings = select_devices(
            [SIM_BOOTED, SIM_SHUTDOWN, REAL], DeviceSelection(count=2))

        assert selected == [REAL, SIM_BOOTED]
        assert warnings == []

    def test_simulator_scope_does_not_force_real_in(self):
        """DeviceScope=simulator 是显式排除真机，真机优先不得越过它。"""
        selected, _ = select_devices(
            [REAL, SIM_BOOTED], DeviceSelection(count=1, scope="simulator"))

        assert selected == [SIM_BOOTED]

    def test_explicit_count_truncates_silently(self):
        """点名要 1 台就 1 台 —— 这是用户主动配置，不是降级，不该刷告警。"""
        selected, warnings = select_devices([SIM_BOOTED, SIM_SHUTDOWN],
                                            DeviceSelection(count=1))

        assert selected == [SIM_BOOTED]
        assert warnings == []

    def test_count_two_mixed_real_and_simulator(self):
        selected, warnings = select_devices(
            [SIM_SHUTDOWN, SIM_BOOTED, REAL],
            DeviceSelection(count=2, mix=["real", "simulator"]),
        )

        assert selected == [REAL, SIM_BOOTED]
        assert warnings == []

    def test_shortage_degrades_with_warning(self):
        """要 2 台只有 1 台 —— 照跑，但必须告警（绝不静默降级）。"""
        selected, warnings = select_devices([SIM_BOOTED], DeviceSelection(count=2))

        assert selected == [SIM_BOOTED]
        assert any("降级为 1 台执行" in w for w in warnings)

    def test_missing_real_device_warns_but_runs(self):
        """DeviceMix 要真机却只有模拟器 —— 这是本功能最关键的一条降级。"""
        selected, warnings = select_devices(
            [SIM_BOOTED], DeviceSelection(count=2, mix=["real", "simulator"]))

        assert selected == [SIM_BOOTED]
        assert any("没有可用的 real 设备" in w for w in warnings)

    def test_scope_matching_nothing_degrades_to_unfiltered(self):
        """DeviceScope=real 但没有真机 —— 「至少一台能跑就执行」优先，忽略过滤并告警。"""
        selected, warnings = select_devices([SIM_BOOTED], DeviceSelection(scope="real"))

        assert selected == [SIM_BOOTED]
        assert any("忽略该过滤条件" in w for w in warnings)

    def test_scope_filter_reports_how_many_were_dropped(self):
        selected, warnings = select_devices(
            [REAL, SIM_BOOTED, SIM_SHUTDOWN], DeviceSelection(scope="simulator"))

        assert selected == [SIM_BOOTED, SIM_SHUTDOWN]
        assert any("过滤掉 1 台设备" in w for w in warnings)

    def test_count_larger_than_pool_uses_all_with_warning(self):
        selected, warnings = select_devices([REAL, SIM_BOOTED], DeviceSelection(count=9))

        assert len(selected) == 2
        assert any("降级为 2 台执行" in w for w in warnings)


class TestResolveExplicitDevices:
    def test_resolves_by_udid_and_keeps_kind(self):
        resolved, warnings = resolve_explicit_devices("ios", [REAL.udid], [SIM_BOOTED, REAL])

        assert resolved == [REAL]
        assert warnings == []

    def test_resolves_by_device_name(self):
        """设备名比 UDID 可读，且换台机器仍稳定。"""
        resolved, warnings = resolve_explicit_devices("ios", ["Tars2"], [SIM_BOOTED, REAL])

        assert resolved == [REAL]
        assert warnings == []

    def test_name_match_is_case_insensitive(self):
        resolved, _ = resolve_explicit_devices("ios", ["tars2"], [REAL])

        assert resolved == [REAL]

    def test_unknown_entry_is_adopted_as_udid_with_warning(self):
        """发现不到的 UDID 仍照用（可能是刚 boot 还没被枚举到），但要告警。"""
        resolved, warnings = resolve_explicit_devices("ios", ["UNKNOWN-UDID"], [])

        assert [d.udid for d in resolved] == ["UNKNOWN-UDID"]
        assert any("不在当前发现结果里" in w for w in warnings)

    def test_mixed_udid_and_name_preserves_order(self):
        resolved, _ = resolve_explicit_devices("ios", ["iPhone 16 Pro", REAL.udid],
                                               [SIM_BOOTED, REAL])

        assert [d.udid for d in resolved] == [SIM_BOOTED.udid, REAL.udid]


class TestFormatDeviceSelection:
    def test_default_config_prints_no_config_line(self):
        lines = format_device_selection([SIM_BOOTED], DeviceSelection(), [])

        assert not any("执行配置" in line for line in lines)

    def test_non_default_config_is_echoed(self):
        lines = format_device_selection(
            [REAL, SIM_BOOTED],
            DeviceSelection(count=2, mix=["real", "simulator"]),
            [],
        )

        assert any("DeviceCount=2" in line and "DeviceMix=real+simulator" in line
                   for line in lines)

    def test_labels_real_and_simulator(self):
        lines = format_device_selection([REAL, SIM_BOOTED],
                                        DeviceSelection(count=2), [])

        assert any("[真机]" in line for line in lines)
        assert any("[模拟器]" in line for line in lines)
        assert any("1 台真机、1 台模拟器" in line for line in lines)

    def test_warnings_are_rendered(self):
        lines = format_device_selection([SIM_BOOTED], DeviceSelection(count=2),
                                        ["DeviceCount=2，实际可用 1 台，降级为 1 台执行"])

        assert any("[WARN]" in line for line in lines)


class TestLoadMobileGroup:
    def _write(self, path, body):
        path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<globalvalue>\n'
                        + body + '\n</globalvalue>\n', encoding="utf-8")

    def test_reads_mobile_group_only(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        self._write(data / "globalvalue.xml",
                    '<group name="Mobile"><var name="Platform" value="ios"/></group>\n'
                    '<group name="Other"><var name="X" value="1"/></group>')

        group = load_mobile_group(tmp_path)

        assert group == {"Platform": "ios"}

    def test_platform_file_overrides_base(self, tmp_path):
        """与 `rodski run --platform` 同一合并语义：平台文件覆盖 globalvalue.xml。"""
        data = tmp_path / "data"
        data.mkdir()
        self._write(data / "globalvalue.xml",
                    '<group name="Mobile">\n'
                    '  <var name="DeviceCount" value="1"/>\n'
                    '  <var name="DeviceName" value="AKRSUT1618000209"/>\n'
                    '</group>')
        self._write(data / "globalvalue_ios.xml",
                    '<group name="Mobile">\n'
                    '  <var name="DeviceCount" value="2"/>\n'
                    '  <var name="DeviceMix" value="real,simulator"/>\n'
                    '</group>')

        group = load_mobile_group(tmp_path, "ios")

        assert group["DeviceCount"] == "2"
        assert group["DeviceMix"] == "real,simulator"
        assert group["DeviceName"] == "AKRSUT1618000209"   # 未被平台文件触碰，保留

    def test_platform_file_not_merged_without_platform(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        self._write(data / "globalvalue.xml",
                    '<group name="Mobile"><var name="DeviceCount" value="1"/></group>')
        self._write(data / "globalvalue_ios.xml",
                    '<group name="Mobile"><var name="DeviceCount" value="2"/></group>')

        assert load_mobile_group(tmp_path)["DeviceCount"] == "1"

    def test_missing_data_dir_is_empty_not_fatal(self, tmp_path):
        assert load_mobile_group(tmp_path) == {}

    def test_malformed_xml_is_empty_not_fatal(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "globalvalue.xml").write_text("<globalvalue><broken>", encoding="utf-8")

        assert load_mobile_group(tmp_path) == {}


class TestIsMultiDeviceConfigured:
    def test_plain_module_is_not_multi_device(self):
        """默认模块不得触发自动转队列 —— 单设备行为必须逐字节不变。"""
        assert is_multi_device_configured({"Platform": "ios", "UDID": "X"}) is False

    def test_none_is_not_multi_device(self):
        assert is_multi_device_configured(None) is False

    @pytest.mark.parametrize("group", [
        {"DeviceCount": "2"},
        {"DeviceMix": "real,simulator"},
        {"DeviceScope": "real"},
        {"DeviceList": "UDID-A"},
    ])
    def test_any_device_variable_triggers_queue(self, group):
        assert is_multi_device_configured(group) is True

    def test_count_one_explicitly_is_not_multi_device(self):
        """写死 DeviceCount=1 是「就要一台」，与不写等价，不得因此转队列。"""
        assert is_multi_device_configured({"DeviceCount": "1"}) is False
