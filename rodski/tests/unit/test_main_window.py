"""MainWindow 单元测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow, TestRunner


@pytest.fixture
def window(qtbot):
    """创建 MainWindow 实例"""
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def test_window_init(window):
    """测试窗口初始化"""
    assert window.windowTitle() == 'SKI 测试框架 v1.0'
    assert window.test_file is None
    assert window.runner is None
    assert window.steps == []
    assert not window.run_btn.isEnabled()


def test_load_test_success(window, qtbot, monkeypatch, tmp_path):
    """测试加载测试文件成功"""
    test_file = tmp_path / "test.xlsx"
    test_file.touch()

    mock_steps = [{'keyword': 'click', 'params': {'target': 'btn'}}]

    monkeypatch.setattr('PyQt6.QtWidgets.QFileDialog.getOpenFileName',
                       lambda *args, **kwargs: (str(test_file), ''))

    with patch('ui.main_window.ExcelParser') as mock_parser:
        mock_parser.return_value.parse.return_value = mock_steps
        window.load_test()

    assert window.test_file == str(test_file)
    assert window.run_btn.isEnabled()
    assert window.tree.topLevelItemCount() == 1


def test_load_test_cancel(window, qtbot, monkeypatch):
    """测试取消加载文件"""
    monkeypatch.setattr('PyQt6.QtWidgets.QFileDialog.getOpenFileName',
                       lambda *args, **kwargs: ('', ''))

    window.load_test()
    assert window.test_file is None


def test_load_test_error(window, qtbot, monkeypatch, tmp_path):
    """测试加载文件失败"""
    test_file = tmp_path / "bad.xlsx"
    test_file.touch()

    monkeypatch.setattr('PyQt6.QtWidgets.QFileDialog.getOpenFileName',
                       lambda *args, **kwargs: (str(test_file), ''))

    with patch('ui.main_window.ExcelParser') as mock_parser:
        mock_parser.side_effect = Exception("Parse error")
        with patch.object(QMessageBox, 'critical'):
            window.load_test()

    assert window.tree.topLevelItemCount() == 0


def test_run_test(window, qtbot, tmp_path):
    """测试运行测试"""
    window.test_file = str(tmp_path / "test.xlsx")

    with patch('ui.main_window.TestRunner') as mock_runner_class:
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        window.run_test()

        assert not window.run_btn.isEnabled()
        assert window.pause_btn.isEnabled()
        assert window.stop_btn.isEnabled()
        mock_runner.start.assert_called_once()


def test_pause_resume_test(window, qtbot):
    """测试暂停和恢复"""
    window.runner = Mock()
    window.runner.paused = False

    window.pause_test()
    window.runner.pause.assert_called_once()

    window.runner.paused = True
    window.pause_test()
    window.runner.resume.assert_called_once()


def test_stop_test(window, qtbot):
    """测试停止测试"""
    window.runner = Mock()

    window.stop_test()

    window.runner.stop.assert_called_once()
    assert window.run_btn.isEnabled()
    assert not window.pause_btn.isEnabled()


def test_append_log(window, qtbot):
    """测试日志追加"""
    window.append_log('INFO', 'Test message')
    assert 'Test message' in window.log_text.toPlainText()

    window.append_log('ERROR', 'Error message')
    assert 'Error message' in window.log_text.toPlainText()


def test_update_progress(window, qtbot):
    """测试进度更新"""
    window.update_progress(5, 10)
    assert window.progress_bar.value() == 5
    assert window.progress_bar.maximum() == 10


def test_update_step_status(window, qtbot):
    """测试步骤状态更新"""
    window.tree.addTopLevelItem(window.tree.invisibleRootItem())
    from PyQt6.QtWidgets import QTreeWidgetItem
    item = QTreeWidgetItem(['1', '待执行', 'click', 'button'])
    window.tree.addTopLevelItem(item)

    window.update_step_status(0, 'PASS', 'Success')

    assert window.tree.topLevelItem(0).text(1) == 'PASS'
    assert window.result_table.rowCount() == 1


def test_test_finished(window, qtbot):
    """测试完成回调"""
    stats = {'total': 10, 'passed': 8, 'failed': 2}

    window.test_finished(stats)

    assert '总数: 10' in window.result_label.text()
    assert '通过: 8' in window.result_label.text()
    assert '失败: 2' in window.result_label.text()
    assert window.run_btn.isEnabled()


def test_show_step_detail(window, qtbot):
    """测试显示步骤详情"""
    from PyQt6.QtWidgets import QTreeWidgetItem
    item = QTreeWidgetItem(['1', '待执行', 'click', 'button'])
    step_data = {'keyword': 'click', 'params': {'target': 'btn'}}
    item.setData(0, Qt.ItemDataRole.UserRole, step_data)

    with patch.object(QMessageBox, 'information') as mock_info:
        window.show_step_detail(item, 0)
        mock_info.assert_called_once()


def test_test_runner_init():
    """测试 TestRunner 初始化"""
    runner = TestRunner('/path/to/test.xlsx')
    assert runner.test_file == '/path/to/test.xlsx'
    assert not runner.stopped
    assert not runner.paused


def test_test_runner_stop():
    """测试 TestRunner 停止"""
    runner = TestRunner('/path/to/test.xlsx')
    runner.stop()
    assert runner.stopped
    assert not runner.paused


def test_test_runner_pause_resume():
    """测试 TestRunner 暂停和恢复"""
    runner = TestRunner('/path/to/test.xlsx')

    runner.pause()
    assert runner.paused

    runner.resume()
    assert not runner.paused
