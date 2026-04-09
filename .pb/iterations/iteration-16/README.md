# Iteration 16: demosite扩展 + 定位器测试

**版本**: v4.8.0  
**分支**: release/v4.8.0  
**日期**: 2026-04-09  
**工时**: 5h  
**优先级**: P0  
**前置依赖**: iteration-15

---

## 目标

扩展 demosite 并添加定位器类型覆盖测试：
1. 扩展 demosite 测试页面（4个新页面）
2. 创建 TC016 定位器类型覆盖测试

---

## 任务清单

### T16-001: 扩展 demosite 测试页面 (3h)

**文件**: 
- `rodski-demo/DEMO/demo_full/demosite/app.py`
- `rodski-demo/DEMO/demo_full/demosite/templates/`

**任务**:
1. 添加 `/locator-test` 页面
   - 包含 id、css、xpath、name 定位器的元素
   - 输入框、按钮、文本显示

2. 添加 `/upload` 页面
   - 文件选择控件
   - 上传按钮
   - 上传结果显示

3. 添加 `/multi-window` 页面
   - 打开新窗口按钮
   - 窗口标识信息

4. 添加 `/iframe-test` 页面
   - 嵌入 iframe
   - iframe 内容页面

**验收**:
- 所有页面可以正常访问
- 页面功能正常工作
- 页面元素有清晰的定位器

---

### T16-002: TC016 定位器类型覆盖测试 (2h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc016_locators.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/LocatorTest.xml`
- `rodski-demo/DEMO/demo_full/data/LocatorTest_verify.xml`

**任务**:
1. 创建测试用例 TC016
2. 添加模型定义：
   - LocatorTest_XPath (使用 xpath 定位)
   - LocatorTest_Name (使用 name 定位)
   - LocatorTest_CSS (使用 css 定位)
3. 添加测试数据和验证数据

**验收**:
- 测试用例可以运行
- 所有定位器类型都能正确定位元素
- 验证通过

---

## 验收标准

- [ ] 4个新页面可以访问
- [ ] TC016 测试通过
- [ ] 覆盖 XPath、Name、CSS 定位器
- [ ] 所有测试用例通过
- [ ] 无回归问题

---

## 工作流程

1. 确认 iteration-15 已完成
2. 创建分支: `git checkout -b release/v4.8.0`
3. 执行 T16-001
4. 执行 T16-002
5. 运行回归测试
6. 更新 record.md
7. 合并到 main: `git merge release/v4.8.0`
8. 打标签: `git tag v4.8.0`

---

## 参考文档

- `.pb/iterations/iteration-14-19-plan.md` - 总体规划
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` - 用例编写指南
