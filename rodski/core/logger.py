"""日志系统 - 文件日志、控制台日志、日志级别"""
import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    def __init__(self, name: str = "rodski", log_dir: str = None, level: str = "INFO",
                 console: bool = True, console_level: str = None, file_level: str = "DEBUG"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        self.console_level = console_level or level
        self.file_level = file_level
        self.file_handler = None
        self.log_dir = None

        if log_dir:
            self.log_dir = Path(log_dir)
            self.set_log_dir(self.log_dir)

        if console:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(getattr(logging, self.console_level.upper(), logging.INFO))
            ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            self.logger.addHandler(ch)
            self.console_handler = ch

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def set_log_dir(self, log_dir: Path) -> None:
        """动态设置日志目录（用于与结果目录同步）"""
        self.log_dir = Path(log_dir)
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()

        log_file = Path(log_dir) / "execution.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(getattr(logging, self.file_level.upper(), logging.DEBUG))
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)
        self.file_handler = fh

    def set_level(self, level: str) -> None:
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    def set_console_level(self, level: str) -> None:
        """动态设置终端输出等级"""
        if hasattr(self, 'console_handler'):
            self.console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    def get_log_files(self) -> list:
        return sorted(self.log_dir.glob("*.log"))

    def get_latest_log(self) -> str:
        files = self.get_log_files()
        if not files:
            return ""
        return files[-1].read_text(encoding="utf-8")

    def clear_logs(self) -> int:
        count = 0
        for f in self.log_dir.glob("*.log"):
            f.unlink()
            count += 1
        return count
