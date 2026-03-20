"""日志系统 - 文件日志、控制台日志、日志级别"""
import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    def __init__(self, name: str = "rodski", log_dir: str = "logs", level: str = "INFO",
                 console: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.handlers.clear()

        log_file = self.log_dir / f"{datetime.now():%Y%m%d}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

        if console:
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            self.logger.addHandler(ch)

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def set_level(self, level: str) -> None:
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

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
