"""RESTful API 测试辅助工具"""
import json
import logging
from typing import Any, Dict, List, Optional
from jsonschema import validate, ValidationError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def build_http_result(status_code: int, body: Any) -> Dict[str, Any]:
    """组装接口步骤的 Return / verify 数据（send 与压测驱动共用）。

    - ``status`` 恒为 HTTP 状态码（CORE §3.3：`_verify` 的 status 列验证 HTTP 状态码）；
    - JSON 对象响应的字段平铺到顶层；响应体自带的 ``status`` 字段不覆盖 HTTP 状态码，
      此时完整响应体放在 ``body`` 中，用 ``body.status`` 读取；
    - 非对象 JSON 或文本响应放在 ``body``；空响应（None / {}）只有 ``status``。
    """
    result: Dict[str, Any] = {}
    if isinstance(body, dict):
        result.update(body)
        if "status" in body:
            result.pop("status")
            result.setdefault("body", body)
    elif body not in (None, ""):
        result["body"] = body
    result["status"] = status_code
    return result


class RestHelper:
    """REST API 测试辅助类"""

    @staticmethod
    def _get_session(max_retries: int = 3, pool_connections: int = 10, pool_maxsize: int = 10) -> requests.Session:
        """获取配置了连接池和重试的 Session"""
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=pool_connections, pool_maxsize=pool_maxsize)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @staticmethod
    def validate_json_schema(data: Dict, schema: Dict) -> bool:
        """验证 JSON Schema"""
        try:
            validate(instance=data, schema=schema)
            return True
        except ValidationError:
            return False

    @staticmethod
    def jsonpath_extract(data: Dict, path: str) -> Any:
        """简单 JSONPath 提取（支持点号路径）"""
        keys = path.strip('$.').split('.')
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    @staticmethod
    def send_request(
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Any = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        use_session: bool = True,
        cookies: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """发送 HTTP 请求"""
        method = method.upper()
        kwargs: Dict[str, Any] = {"headers": headers, "timeout": timeout}
        if body is not None:
            kwargs["json"] = body
        if cookies:
            kwargs["cookies"] = cookies

        try:
            logger.debug(f"Sending {method} request to {url}")
            if use_session:
                session = RestHelper._get_session(max_retries=max_retries)
                response = session.request(method, url, **kwargs)
            else:
                response = requests.request(method, url, **kwargs)
            logger.debug(f"Response: {response.status_code} in {response.elapsed.total_seconds():.3f}s")
            return response
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {str(e)}")
            raise

    @staticmethod
    def assert_response_time(response: requests.Response, max_ms: float) -> bool:
        """断言响应时间（毫秒）"""
        elapsed_ms = response.elapsed.total_seconds() * 1000
        return elapsed_ms <= max_ms

    @staticmethod
    def extract_headers(response: requests.Response, header_name: str) -> Optional[str]:
        """提取响应头"""
        return response.headers.get(header_name)

    @staticmethod
    def compare_responses(
        resp1: Dict,
        resp2: Dict,
        ignore_fields: Optional[List[str]] = None,
    ) -> bool:
        """比较两个响应（忽略指定字段）"""
        ignore_fields = ignore_fields or []

        def _strip(d: Any) -> Any:
            if isinstance(d, dict):
                return {k: _strip(v) for k, v in d.items() if k not in ignore_fields}
            if isinstance(d, list):
                return [_strip(i) for i in d]
            return d

        return _strip(resp1) == _strip(resp2)
