"""LLM-based Test Result Reviewer"""
import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from openai import OpenAI


class LLMReviewer:
    """使用 LLM 审查测试结果的真实性"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "llm_config.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        api_key = self.config.get('api_key')
        if api_key == 'your-api-key-here':
            api_key = os.getenv('OPENAI_API_KEY')

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.config.get('api_base')
        )

    def review_result(self, result_dir: str, case_xml: str = None) -> Dict:
        """审查测试结果

        Args:
            result_dir: 测试结果目录
            case_xml: 测试用例 XML 路径（可选）

        Returns:
            审查结果字典
        """
        result_path = Path(result_dir)

        # 读取执行日志
        log_file = result_path / "execution.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()

        # 读取结果 XML
        result_xml = result_path / "result.xml"
        with open(result_xml, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # 收集截图
        screenshots = self._collect_screenshots(result_path)

        # 构建审查请求
        return self._call_llm(log_content, xml_content, screenshots, case_xml)

    def _collect_screenshots(self, result_path: Path) -> List[str]:
        """收集截图文件路径"""
        screenshot_dir = result_path / "screenshots"
        if not screenshot_dir.exists():
            return []

        max_count = self.config['review']['max_screenshots']
        screenshots = sorted(screenshot_dir.glob("*.png"))
        return [str(s) for s in screenshots[:max_count]]

    def _encode_image(self, image_path: str) -> str:
        """将图片编码为 base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _call_llm(self, log: str, result_xml: str, screenshots: List[str], case_xml: Optional[str]) -> Dict:
        """调用 LLM 进行审查"""
        messages = [
            {"role": "system", "content": self.config['review']['system_prompt']},
            {"role": "user", "content": self._build_user_prompt(log, result_xml, case_xml)}
        ]

        # 添加截图（如果启用 vision）
        if self.config['review']['enable_vision'] and screenshots:
            image_contents = []
            for img_path in screenshots:
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{self._encode_image(img_path)}"}
                })
            messages.append({"role": "user", "content": image_contents})

        response = self.client.chat.completions.create(
            model=self.config['model'],
            messages=messages,
            temperature=self.config['temperature'],
            max_tokens=self.config['max_tokens']
        )

        result_text = response.choices[0].message.content
        return json.loads(result_text)

    def _build_user_prompt(self, log: str, result_xml: str, case_xml: Optional[str]) -> str:
        """构建用户提示词"""
        prompt = f"""请审查以下测试结果：

## 测试结果 XML
```xml
{result_xml}
```

## 执行日志（前 3000 字符）
```
{log[:3000]}
```
"""
        if case_xml:
            with open(case_xml, 'r', encoding='utf-8') as f:
                prompt += f"\n## 测试用例定义\n```xml\n{f.read()}\n```\n"

        prompt += "\n请根据以上信息和截图，判断测试是否真正成功。"
        return prompt
