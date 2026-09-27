import sys
from pathlib import Path

import pytest

try:
    from rodski import ski_run
except ImportError:  # Running pytest with rodski/ as the working directory.
    import ski_run


class _FakeConfig:
    def __init__(self, *args, **kwargs):
        self.config = {"recording": {}}

    def get(self, key, default=None):
        return self.config.get(key, default)


class _FakeExecutor:
    results = []
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.closed = False
        self.__class__.last_instance = self

    def execute_all_cases(self):
        return list(self.__class__.results)

    def close(self):
        self.closed = True


def _prepare_case_module(tmp_path: Path) -> tuple[Path, Path]:
    module_dir = tmp_path / "module"
    case_dir = module_dir / "case"
    (module_dir / "model").mkdir(parents=True)
    case_dir.mkdir()
    (module_dir / "model" / "model.xml").write_text("<models />", encoding="utf-8")
    (case_dir / "case.xml").write_text("<cases />", encoding="utf-8")
    return module_dir, case_dir


def _patch_runner(monkeypatch, module_dir: Path, results):
    _FakeExecutor.results = results
    _FakeExecutor.last_instance = None

    monkeypatch.setattr(ski_run, "Logger", lambda *args, **kwargs: None)
    monkeypatch.setattr(ski_run, "ConfigManager", _FakeConfig)
    monkeypatch.setattr(ski_run, "SKIExecutor", _FakeExecutor)
    monkeypatch.setattr(ski_run, "resolve_module_dir", lambda _path: module_dir)
    monkeypatch.setattr(ski_run, "_needs_browser", lambda _path: False)


@pytest.mark.parametrize(
    ("results", "expected_exit_code"),
    [
        ([{"case_id": "TC-PASS", "status": "PASS"}], 0),
        ([{"case_id": "TC-FAIL", "status": "FAIL"}], 1),
    ],
)
def test_main_returns_nonzero_only_when_a_case_fails(
    monkeypatch, tmp_path, results, expected_exit_code
):
    module_dir, case_dir = _prepare_case_module(tmp_path)
    _patch_runner(monkeypatch, module_dir, results)
    monkeypatch.setattr(sys, "argv", ["ski_run.py", str(case_dir)])

    assert ski_run.main() == expected_exit_code
    assert _FakeExecutor.last_instance is not None
    assert _FakeExecutor.last_instance.closed is True


def test_missing_case_path_keeps_existing_nonzero_cli_error(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.xml"
    monkeypatch.setattr(sys, "argv", ["ski_run.py", str(missing_path)])

    with pytest.raises(SystemExit) as exc_info:
        ski_run.main()

    assert exc_info.value.code == 1
