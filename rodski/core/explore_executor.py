"""探索执行器 - 提供 execute_command() API 用于探索式测试

v9.0.0 新架构：
- rodski-agent 调用 execute_command() 执行单个原子命令
- 返回 ExecutionResult {success, evidence, errors}
- 不参与探索决策，只负责执行和采集证据
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from .keyword_engine import KeywordEngine
    from .exceptions import SKIError
except ImportError:
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.exceptions import SKIError

logger = logging.getLogger("rodski")


class ExploreExecutor:
    """探索执行器 - 执行单个探索命令并采集证据

    职责：
    1. 执行单个原子命令（引用 model.xml + data.sqlite）
    2. 采集执行证据（screenshot / url / return_value / browser_errors）
    3. 返回结构化 ExecutionResult
    4. 不参与探索决策和 finding 分类
    """

    def __init__(self, keyword_engine: KeywordEngine, module_dir: Path):
        """初始化探索执行器

        Args:
            keyword_engine: 关键字引擎实例
            module_dir: 模块目录路径（用于定位 model.xml / data.sqlite）
        """
        self.keyword_engine = keyword_engine
        self.module_dir = module_dir
        self._session_id: Optional[str] = None
        self._step_counter = 0

    def start_session(self, session_id: str) -> None:
        """开始探索会话

        Args:
            session_id: 探索会话 ID
        """
        self._session_id = session_id
        self._step_counter = 0
        logger.info(f"[ExploreExecutor] Start session: {session_id}")

    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个探索命令

        Args:
            command: 命令字典，格式：
                {
                    "action": str,      # 关键字动作（type/click/verify/get 等）
                    "model": str,       # 引用 model.xml 中的模型名称
                    "data": str         # 引用 data.sqlite 中的 data_id（可选）
                }

        Returns:
            ExecutionResult: 执行结果字典
                {
                    "success": bool,              # 执行是否成功
                    "evidence": {                 # 执行证据
                        "screenshot": str,        # 截图路径
                        "url": str,               # 当前 URL
                        "return_value": Any,      # 返回值
                        "browser_errors": list    # 浏览器错误（来自 rodski-explorer 插件）
                    },
                    "errors": list                # 错误信息列表
                }
        """
        self._step_counter += 1
        step_id = f"{self._session_id}_step_{self._step_counter}"

        logger.info(f"[ExploreExecutor] Execute command: {command}")

        try:
            # 1. 验证命令格式
            self._validate_command(command)

            # 2. 执行命令（调用 KeywordEngine）
            self._execute_action(command)

            # 3. 采集证据
            evidence = self._collect_evidence(step_id)

            return {
                "success": True,
                "evidence": evidence,
                "errors": []
            }

        except Exception as e:
            logger.error(f"[ExploreExecutor] Command execution failed: {e}")

            # 执行失败，仍然采集证据
            evidence = self._collect_evidence(step_id)

            return {
                "success": False,
                "evidence": evidence,
                "errors": [str(e)]
            }

    def _validate_command(self, command: Dict[str, Any]) -> None:
        """验证命令格式

        Args:
            command: 命令字典

        Raises:
            SKIError: 命令格式错误
        """
        if "action" not in command:
            raise SKIError("Command missing 'action' field")

        if "model" not in command:
            raise SKIError("Command missing 'model' field")

        action = command["action"]
        if action not in self.keyword_engine.SUPPORTED:
            raise SKIError(f"Unsupported action: {action}")

    def _execute_action(self, command: Dict[str, Any]) -> None:
        """执行命令动作

        Args:
            command: 命令字典
        """
        action = command["action"]
        model_name = command.get("model", "")
        data_id = command.get("data")

        # 构造参数字典（KeywordEngine.execute() 期望的格式）
        params = {
            "model": model_name,
        }

        if data_id:
            params["data"] = data_id

        # 调用 KeywordEngine.execute() 执行关键字
        self.keyword_engine.execute(keyword=action, params=params)

    def _collect_evidence(self, step_id: str) -> Dict[str, Any]:
        """采集执行证据

        Args:
            step_id: 步骤 ID

        Returns:
            证据字典
        """
        evidence = {
            "screenshot": None,
            "url": None,
            "return_value": None,
            "browser_errors": []
        }

        try:
            # 1. 采集截图
            driver = self.keyword_engine.driver
            if driver and hasattr(driver, "screenshot"):
                screenshot_path = self._take_screenshot(step_id)
                evidence["screenshot"] = screenshot_path

            # 2. 采集当前 URL
            if driver and hasattr(driver, "current_url"):
                evidence["url"] = driver.current_url()

            # 3. 采集返回值（从 RuntimeContext）
            context = self.keyword_engine._context
            if context and hasattr(context, "get_return"):
                evidence["return_value"] = context.get_return(-1)

            # 4. 采集浏览器错误（如果 rodski-explorer 插件已激活）
            if self._is_explorer_active():
                browser_errors = self._collect_explorer_evidence(step_id)
                evidence["browser_errors"] = browser_errors

        except Exception as e:
            logger.warning(f"[ExploreExecutor] Evidence collection failed: {e}")

        return evidence

    def _take_screenshot(self, step_id: str) -> str:
        """截图并返回路径

        Args:
            step_id: 步骤 ID

        Returns:
            截图文件路径
        """
        screenshot_path = f"{self.module_dir}/result/explore/{step_id}.png"
        self.keyword_engine.driver.screenshot(screenshot_path)
        return screenshot_path

    def _is_explorer_active(self) -> bool:
        """检查 rodski-explorer 插件是否已激活

        Returns:
            是否已激活
        """
        driver = self.keyword_engine.driver

        if not hasattr(driver, "page") or not driver.page:
            return False

        try:
            # 检查页面是否有插件注入的标记
            is_active = driver.page.evaluate("""
                () => {
                    return typeof window.__rodski_explorer__ !== 'undefined';
                }
            """)
            return bool(is_active)
        except Exception:
            return False

    def _collect_explorer_evidence(self, step_id: str) -> list:
        """收集 rodski-explorer 插件证据

        Args:
            step_id: 步骤 ID

        Returns:
            浏览器错误列表
        """
        # TODO: 实现插件证据收集逻辑
        # 从 localStorage 读取插件采集的错误信息
        return []
