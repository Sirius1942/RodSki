"""模型定位器 → Playwright 选择器（唯一实现）

驱动的 `_convert_locator`（type / click / get_text 等）与 KeywordEngine 的元素状态断言
（$count / $exists / $visible、iframe 内读取）都经由这里转换，避免两处语义不一致
（v11.8.25 BUG-A24 / A25：class 多类名、tag 定位器此前只在后者可用）。
"""

# 模型 <location type="..."> 中可转换为 Web 选择器的传统定位器类型（model.xsd LocatorType）
WEB_LOCATOR_TYPES = ('id', 'class', 'css', 'xpath', 'text', 'name', 'tag')


def to_playwright_selector(locator_type: str, locator_value: str) -> str:
    """把 (定位器类型, 定位值) 转换为 Playwright 选择器。

    - id    → `[id="值"]`（属性选择器，id 含 `.`/`:` 或以数字开头也可用）
    - class → `.a.b`（值是 class 属性原文，多个类名空格分隔，表示同时具备）
    - css / tag → 原值（tag 即标签名选择器）
    - xpath → `xpath=值`（显式引擎前缀，`(//a)[1]` 之类写法也不会被当作 CSS）
    - text  → `text=值`
    - name  → `[name="值"]`
    """
    if locator_type == 'id':
        return f'[id="{locator_value}"]'
    if locator_type == 'class':
        return ''.join(f'.{c}' for c in locator_value.split())
    if locator_type in ('css', 'tag'):
        return locator_value
    if locator_type == 'xpath':
        return f'xpath={locator_value}'
    if locator_type == 'text':
        return f'text={locator_value}'
    if locator_type == 'name':
        return f'[name="{locator_value}"]'
    return f'{locator_type}={locator_value}'


def convert_locator(locator: str) -> str:
    """转换 `类型=值` 形式的定位器字符串；已是选择器（`#x`、`.x`、`[..]` 等）的原样返回。"""
    for locator_type in WEB_LOCATOR_TYPES:
        prefix = f'{locator_type}='
        if locator.startswith(prefix):
            return to_playwright_selector(locator_type, locator[len(prefix):])
    return locator
