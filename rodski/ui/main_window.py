"""SKI 测试框架 PyQt6 主界面"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit, QLabel,
    QFileDialog, QSplitter, QMessageBox, QProgressBar, QComboBox,
    QTabWidget, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QShortcut

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.excel_parser import ExcelParser
from core.keyword_engine import KeywordEngine
from core.task_executor import TaskExecutor


class TestRunner(QThread):
    """测试执行线程"""
    log_signal = pyqtSignal(str, str)
    step_signal = pyqtSignal(int, str, str)  # index, status, message
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, test_file):
        super().__init__()
        self.test_file = test_file
        self.stopped = False
        self.paused = False
    
    def run(self):
        try:
            parser = ExcelParser(self.test_file)
            steps = parser.parse()
            
            engine = KeywordEngine()
            executor = TaskExecutor(engine)
            
            total = len(steps)
            self.log_signal.emit('INFO', f'开始执行 {total} 个步骤')
            
            for i, step in enumerate(steps):
                if self.stopped:
                    break
                
                while self.paused and not self.stopped:
                    self.msleep(100)
                
                if self.stopped:
                    break
                
                keyword = step.get('keyword', '')
                self.log_signal.emit('INFO', f'执行步骤 {i+1}: {keyword}')
                self.step_signal.emit(i, 'RUNNING', '')
                
                try:
                    result = engine.execute(keyword, step.get('params', {}))
                    status = 'PASS' if result.get('success') else 'FAIL'
                    msg = result.get('message', '')
                    self.step_signal.emit(i, status, msg)
                    self.log_signal.emit('INFO' if status == 'PASS' else 'ERROR', 
                                        f'步骤 {i+1} {status}: {msg}')
                except Exception as e:
                    self.step_signal.emit(i, 'FAIL', str(e))
                    self.log_signal.emit('ERROR', f'步骤 {i+1} 失败: {str(e)}')
                
                self.progress_signal.emit(i + 1, total)
            
            if not self.stopped:
                passed = sum(1 for r in executor.results if r.get('status') == 'PASS')
                failed = len(executor.results) - passed
                stats = {'total': len(executor.results), 'passed': passed, 'failed': failed}
                self.finished_signal.emit(stats)
                self.log_signal.emit('INFO', '测试执行完成')
        except Exception as e:
            self.log_signal.emit('ERROR', f'执行失败: {str(e)}')
    
    def stop(self):
        self.stopped = True
        self.paused = False
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.test_file = None
        self.runner = None
        self.steps = []
        self.init_ui()
        self.setup_shortcuts()
    
    def init_ui(self):
        self.setWindowTitle('SKI 测试框架 v1.0')
        self.setGeometry(100, 100, 1400, 900)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['步骤', '状态', '关键字', '目标'])
        self.tree.setColumnWidth(0, 80)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 120)
        self.tree.itemDoubleClicked.connect(self.show_step_detail)
        splitter.addWidget(self.tree)
        
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([500, 900])
        layout.addWidget(splitter)
        
        self.status_label = QLabel('就绪')
        self.statusBar().addWidget(self.status_label)
    
    def _create_toolbar(self):
        layout = QHBoxLayout()
        
        self.load_btn = QPushButton('📂 加载用例')
        self.load_btn.clicked.connect(self.load_test)
        layout.addWidget(self.load_btn)
        
        self.run_btn = QPushButton('▶️ 开始')
        self.run_btn.clicked.connect(self.run_test)
        self.run_btn.setEnabled(False)
        layout.addWidget(self.run_btn)
        
        self.pause_btn = QPushButton('⏸️ 暂停')
        self.pause_btn.clicked.connect(self.pause_test)
        self.pause_btn.setEnabled(False)
        layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton('⏹️ 停止')
        self.stop_btn.clicked.connect(self.stop_test)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        layout.addWidget(QLabel('日志级别:'))
        self.log_filter = QComboBox()
        self.log_filter.addItems(['全部', 'INFO', 'ERROR'])
        self.log_filter.currentTextChanged.connect(self.filter_logs)
        layout.addWidget(self.log_filter)
        
        layout.addStretch()
        return layout
    
    def _create_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.result_label = QLabel('总数: 0 | 通过: 0 | 失败: 0')
        self.result_label.setStyleSheet('font-weight: bold; font-size: 14px;')
        layout.addWidget(self.result_label)
        
        tabs = QTabWidget()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        tabs.addTab(self.log_text, '📋 日志')
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(['步骤', '状态', '关键字', '消息'])
        tabs.addTab(self.result_table, '📊 结果')
        
        layout.addWidget(tabs)
        return widget
    
    def setup_shortcuts(self):
        QShortcut(QKeySequence('Ctrl+O'), self, self.load_test)
        QShortcut(QKeySequence('F5'), self, self.run_test)
        QShortcut(QKeySequence('Esc'), self, self.stop_test)
    
    def load_test(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择测试文件', '', 'Excel Files (*.xlsx);;All Files (*)'
        )
        
        if file_path:
            self.test_file = file_path
            self.load_test_tree(file_path)
            self.run_btn.setEnabled(True)
            self.status_label.setText(f'已加载: {Path(file_path).name}')
    
    def load_test_tree(self, file_path):
        self.tree.clear()
        self.result_table.setRowCount(0)
        try:
            parser = ExcelParser(file_path)
            self.steps = parser.parse()
            
            for i, step in enumerate(self.steps):
                keyword = step.get('keyword', '')
                params = step.get('params', {})
                target = params.get('target', params.get('locator', params.get('text', '')))
                
                item = QTreeWidgetItem(self.tree, [
                    f'{i+1}', '待执行', keyword, str(target)[:50]
                ])
                item.setData(0, Qt.ItemDataRole.UserRole, step)
            
            self.tree.expandAll()
            self.status_label.setText(f'已加载 {len(self.steps)} 个步骤')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载失败: {str(e)}')
    
    def run_test(self):
        if not self.test_file:
            return
        
        self.log_text.clear()
        self.result_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.run_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.status_label.setText('执行中...')
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setText(1, '待执行')
            item.setBackground(1, QColor(255, 255, 255))
        
        self.runner = TestRunner(self.test_file)
        self.runner.log_signal.connect(self.append_log)
        self.runner.step_signal.connect(self.update_step_status)
        self.runner.progress_signal.connect(self.update_progress)
        self.runner.finished_signal.connect(self.test_finished)
        self.runner.start()
    
    def pause_test(self):
        if self.runner:
            if self.runner.paused:
                self.runner.resume()
                self.pause_btn.setText('⏸️ 暂停')
                self.status_label.setText('执行中...')
            else:
                self.runner.pause()
                self.pause_btn.setText('▶️ 继续')
                self.status_label.setText('已暂停')
    
    def stop_test(self):
        if self.runner:
            self.runner.stop()
            self.status_label.setText('已停止')
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
    
    def update_step_status(self, index, status, message):
        if index < self.tree.topLevelItemCount():
            item = self.tree.topLevelItem(index)
            item.setText(1, status)
            
            if status == 'RUNNING':
                item.setBackground(1, QColor(255, 255, 200))
            elif status == 'PASS':
                item.setBackground(1, QColor(200, 255, 200))
            elif status == 'FAIL':
                item.setBackground(1, QColor(255, 200, 200))
            
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            self.result_table.setItem(row, 0, QTableWidgetItem(str(index + 1)))
            self.result_table.setItem(row, 1, QTableWidgetItem(status))
            self.result_table.setItem(row, 2, QTableWidgetItem(item.text(2)))
            self.result_table.setItem(row, 3, QTableWidgetItem(message))
    
    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f'执行中... ({current}/{total})')
    
    def append_log(self, level, message):
        color = {'INFO': 'black', 'ERROR': 'red', 'WARN': 'orange'}.get(level, 'black')
        self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')
    
    def filter_logs(self, level):
        pass  # 简化实现，实际可以过滤日志
    
    def show_step_detail(self, item, column):
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step:
            detail = f"关键字: {step.get('keyword', '')}\n"
            detail += f"参数: {step.get('params', {})}\n"
            detail += f"预期: {step.get('expected', '')}"
            QMessageBox.information(self, '步骤详情', detail)
    
    def test_finished(self, stats):
        self.result_label.setText(
            f"总数: {stats['total']} | 通过: {stats['passed']} | 失败: {stats['failed']}"
        )
        self.status_label.setText('执行完成')
        self.run_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText('⏸️ 暂停')
        self.stop_btn.setEnabled(False)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

