# Iteration 04: 设计文档

**版本**: v1.0
**日期**: 2026-04-03

---

## 1. 架构设计

### 1.1 日志系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    SKIExecutor                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Logger (Singleton)                   │  │
│  │  ┌────────────────┐      ┌────────────────────┐  │  │
│  │  │ Console Handler│      │  File Handler      │  │  │
│  │  │  (可配置等级)   │      │  (固定 DEBUG)      │  │  │
│  │  └────────┬───────┘      └────────┬───────────┘  │  │
│  │           │                       │              │  │
│  │           ▼                       ▼              │  │
│  │      终端输出              execution.log         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 结果目录结构

```
result/
├── run_20260403_153045/
│   ├── result.xml
│   ├── execution.log
│   ├── metadata.json
│   └── screenshots/
│       ├── case1_failure.png
│       └── case2_step3.png
└── run_20260403_160230/
    ├── result.xml
    ├── execution.log
    └── screenshots/
```

---

## 2. 核心类设计

### 2.1 Logger 类重构

```python
class Logger:
    """日志管理器（单例模式）"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self, 
        name: str = "rodski",
        log_dir: Optional[Path] = None,
        console_level: str = "INFO",
        file_level: str = "DEBUG"
    ):
        """
        Args:
            name: logger 名称
            log_dir: 日志目录（None 则不写文件）
            console_level: 终端输出等级
            file_level: 文件输出等级
        """
        pass
    
    def set_log_dir(self, log_dir: Path) -> None:
        """动态设置日志目录（用于与结果目录同步）"""
        pass
    
    def set_console_level(self, level: str) -> None:
        """动态设置终端输出等级"""
        pass
```

### 2.2 ResultWriter 类重构

```python
class ResultWriter:
    """结果写入器"""
    
    def __init__(self, result_base_dir: str):
        """
        Args:
            result_base_dir: 结果根目录（如 data/result/）
        """
        # 创建本次执行目录
        self.run_dir = self._create_run_dir(result_base_dir)
        self.result_file = self.run_dir / "result.xml"
        self.log_file = self.run_dir / "execution.log"
        self.screenshot_dir = self.run_dir / "screenshots"
        
        # 同步日志目录到 Logger
        logger.set_log_dir(self.run_dir)
    
    def _create_run_dir(self, base_dir: str) -> Path:
        """创建 run_YYYYMMDD_HHMMSS 目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path(base_dir) / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "screenshots").mkdir(exist_ok=True)
        return run_dir
```

---

## 3. 日志格式设计

### 3.1 文件日志格式

```
2026-04-03 15:30:45,123 [INFO] 开始执行用例: c001 - 登录测试
2026-04-03 15:30:45,125 [DEBUG] 用例配置: execute=是, component_type=界面
2026-04-03 15:30:45,130 [INFO]   [预处理] 执行 1 个步骤
2026-04-03 15:30:45,135 [INFO]     步骤 1: navigate  GlobalValue.DefaultValue.URL
2026-04-03 15:30:46,200 [INFO]   [用例阶段] 执行 2 个步骤
2026-04-03 15:30:46,205 [INFO]     步骤 1: type Login L001
2026-04-03 15:30:46,210 [DEBUG]     解析后数据: {'username': 'admin', 'password': 'admin123'}
2026-04-03 15:30:47,500 [INFO]     步骤 2: verify Login V001
2026-04-03 15:30:47,800 [INFO] 用例执行完成: c001 - PASS (耗时 2.68s)
```

### 3.2 终端输出格式

```
[INFO] 开始执行用例: c001 - 登录测试
[INFO]   [预处理] 执行 1 个步骤
[INFO]     步骤 1: navigate  GlobalValue.DefaultValue.URL
[INFO]   [用例阶段] 执行 2 个步骤
[INFO]     步骤 1: type Login L001
[INFO]     步骤 2: verify Login V001
[INFO] 用例执行完成: c001 - PASS (耗时 2.68s)
```

---

## 4. CLI 参数设计

```bash
# 默认（INFO 等级）
python ski_run.py case/demo.xml

# 调试模式（DEBUG 等级）
python ski_run.py case/demo.xml --verbose
python ski_run.py case/demo.xml --log-level DEBUG

# 静默模式（仅 ERROR）
python ski_run.py case/demo.xml --quiet
python ski_run.py case/demo.xml --log-level ERROR

# 自定义等级
python ski_run.py case/demo.xml --log-level WARNING
```

---

## 5. 实现优先级

### P0（必须）
- 结果目录重构（run_* 目录）
- 日志文件生成（execution.log）
- 双 Handler 输出（Console + File）

### P1（重要）
- 日志等级梳理（替换 print）
- CLI 参数支持（--log-level）

### P2（可选）
- metadata.json 生成
- 日志轮转
- 结构化日志
