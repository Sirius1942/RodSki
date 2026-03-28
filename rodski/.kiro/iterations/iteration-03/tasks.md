# Iteration 03 任务清单

## Phase 1: Critical Bug 修复 (2天)

### T3-001: 修复 VisionLocator 导入错误
- 更新 vision/locator.py 导入路径
- 验证 vision 定位器可用
**预计**: 2h

### T3-002: 补全 requirements.txt 依赖
- 添加 requests, pillow, pyyaml, anthropic, openai
- 验证依赖安装
**预计**: 1h

### T3-003: 重构 BaseDriver 接口
- 统一为坐标接口
- 更新所有驱动实现
**预计**: 8h

## Phase 2: High Priority 修复 (2天)

### T3-004: 解决 click 关键字矛盾
- 从 XSD 移除或加入 SUPPORTED
**预计**: 2h

### T3-005: 删除 DataParser 死代码
- 删除 data_parser.py 和 excel_parser.py
**预计**: 1h

### T3-006: 修复 DriverFactory 缓存
- 改为实例变量或添加配置检查
**预计**: 4h

## Phase 3: 验证测试 (1天)

### T3-007: 集成测试
- Web 自动化测试
- Vision 定位测试
- API 测试
**预计**: 6h
