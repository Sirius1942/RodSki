"""LLM 异常定义"""


class LLMError(Exception):
    """LLM 基础异常"""
    pass


class LLMProviderError(LLMError):
    """Provider 调用失败"""
    pass


class LLMConfigError(LLMError):
    """配置错误"""
    pass


class LLMTimeoutError(LLMError):
    """调用超时"""
    pass
