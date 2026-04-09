# Iteration 15: 验收测试

## 设计合规性检查

| 检查项 | 结论 |
|--------|------|
| 不改变 rodski 框架代码 | ✅ |
| 所有新增功能向后兼容 | ✅ |
| 新增测试用例可独立运行 | ✅ |
| 文档同步更新 | ✅ |

---

## AC15-001: 定位器类型覆盖验证

**测试用例名称**: TC016 定位器类型覆盖测试

**验收条件**:
- XPath 定位器可以正确定位元素
- Name 定位器可以正确定位元素
- CSS 定位器可以正确定位元素
- 所有定位器类型的元素都能正确操作
- 验证通过

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc016_locators.xml
```

**验证方法**:
1. 测试用例运行成功
2. 所有定位器都能找到元素
3. 操作执行正确
4. 验证结果正确

---

## AC15-002: 关键字完整覆盖验证

**测试用例名称**: TC017 关键字完整覆盖测试

**验收条件**:
- wait 关键字等待时间正确
- clear 关键字清空输入成功
- screenshot 关键字生成截图文件
- assert 关键字断言正确
- upload_file 关键字上传文件成功
- 所有关键字执行无错误

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc017_keywords.xml
```

**验证方法**:
1. 测试用例运行成功
2. 检查截图文件存在
3. 检查上传文件成功
4. 所有断言通过

---

## AC15-003: 视觉定位功能验证（可选）

**测试用例名称**: TC018 视觉定位功能测试

**验收条件**:
- vision 定位器模型定义正确
- vision_bbox 定位器模型定义正确
- 测试用例结构完整
- 文档说明清晰（需要 OmniParser 服务）
- 有服务时可以运行

**运行方式**: 
```bash
# 需要先启动 OmniParser 服务
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc018_vision.xml
```

**验证方法**:
1. 模型定义符合规范
2. 测试用例可以解析
3. 文档说明依赖关系
4. 有服务时运行成功

---

## AC15-004: 桌面应用自动化验证

**测试用例名称**: TC019 桌面应用自动化测试

**验收条件**:
- launch 关键字可以启动应用
- run 关键字可以执行脚本
- 桌面操作脚本正常工作
- 支持 Windows/macOS 平台
- 文档说明平台差异

**运行方式**: 
```bash
# Windows
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc019_desktop.xml

# macOS
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc019_desktop.xml
```

**验证方法**:
1. 应用可以启动
2. 脚本可以执行
3. 操作正确完成
4. 不同平台都能运行

---

## AC15-005: 多窗口和 iframe 验证

**测试用例名称**: TC020 多窗口和 iframe 测试

**验收条件**:
- 可以打开新窗口
- 可以切换窗口
- 可以切换 iframe
- 在不同窗口/iframe 中操作正确
- 验证通过

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc020_windows.xml
```

**验证方法**:
1. 新窗口打开成功
2. 窗口切换正确
3. iframe 切换正确
4. 验证结果正确

---

## AC15-006: 复杂数据引用验证

**测试用例名称**: TC021 复杂数据引用测试

**验收条件**:
- GlobalValue 引用正确解析
- Return 嵌套引用正确
- 命名变量读写正确
- 复杂数据路径访问正确
- 验证通过

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc021_data_ref.xml
```

**验证方法**:
1. GlobalValue 引用值正确
2. Return 嵌套访问成功
3. 命名变量存取正确
4. 验证结果正确

---

## AC15-007: 负面测试集合验证

**测试用例名称**: TC022-TC024 负面测试

**验收条件**:
- TC022（元素不存在）正确标记为预期失败
- TC023（接口错误）正确标记为预期失败
- TC024（SQL错误）正确标记为预期失败
- 测试报告统计正确
- 不影响整体测试结果

**运行方式**: 
```bash
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc022_negative.xml
```

**验证方法**:
1. 所有负面用例显示为预期失败
2. 测试报告统计准确
3. 整体测试结果正确

---

## AC15-008: 功能覆盖率验证

**测试用例名称**: 完整功能覆盖测试

**验收条件**:
- 关键字覆盖率达到 89% (16/18)
- 定位器覆盖率达到 100% (6/6)
- 高级特性覆盖率达到 100% (10/10)
- 总体功能覆盖率达到 90%+

**验证方法**:
1. 统计所有关键字使用情况
2. 统计所有定位器使用情况
3. 统计所有高级特性使用情况
4. 计算总体覆盖率

**覆盖率矩阵**:

### 关键字覆盖
| 关键字 | 覆盖用例 | 状态 |
|--------|---------|------|
| navigate | TC001-TC021 | ✅ |
| type | TC001-TC021 | ✅ |
| verify | TC001-TC021 | ✅ |
| send | TC004, TC005, TC014 | ✅ |
| DB | TC006, TC024 | ✅ |
| close | TC001-TC021 | ✅ |
| wait | TC017 | ✅ |
| clear | TC017 | ✅ |
| screenshot | TC017 | ✅ |
| assert | TC017 | ✅ |
| upload_file | TC017 | ✅ |
| get | TC009, TC010, TC011, TC012B, TC021 | ✅ |
| set | TC010, TC015, TC021 | ✅ |
| run | TC007, TC019, TC020 | ✅ |
| evaluate | TC012 | ✅ |
| launch | TC019 | ✅ |

### 定位器覆盖
| 定位器 | 覆盖用例 | 状态 |
|--------|---------|------|
| id | TC001-TC015 | ✅ |
| css | TC016 | ✅ |
| xpath | TC016 | ✅ |
| name | TC016 | ✅ |
| vision | TC018 | ✅ |
| vision_bbox | TC018 | ✅ |

### 高级特性覆盖
| 特性 | 覆盖用例 | 状态 |
|------|---------|------|
| Auto Capture | TC013, TC014 | ✅ |
| Return引用 | TC009, TC009A, TC021 | ✅ |
| set/get | TC010, TC015, TC021 | ✅ |
| expect_fail | TC012A, TC014A, TC022-TC024 | ✅ |
| GlobalValue | TC021 | ✅ |
| evaluate结构化 | TC012 | ✅ |
| pre/post_process | TC002-TC021 | ✅ |
| 视觉定位 | TC018 | ✅ |
| 桌面自动化 | TC019 | ✅ |
| 窗口切换 | TC020 | ✅ |

---

## AC15-009: 文档完整性验证

**测试用例名称**: 文档更新验证

**验收条件**:
- README.md 包含所有新增用例说明
- COVERAGE.md 详细说明功能覆盖情况
- 所有新增功能都有文档说明
- 文档与代码同步

**验证方法**:
1. 阅读 README.md，检查完整性
2. 阅读 COVERAGE.md，检查覆盖率说明
3. 验证文档与实际代码一致

---

## AC15-010: 完整回归测试验证

**测试用例名称**: 所有测试用例通过

**验收条件**:
- 所有现有测试用例（TC001-TC015）通过
- 所有新增测试用例（TC016-TC024）通过
- 测试报告统计准确
- 无回归问题

**运行方式**: 
```bash
# 运行所有测试用例
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc016_locators.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc017_keywords.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc018_vision.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc019_desktop.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc020_windows.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc021_data_ref.xml
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/tc022_negative.xml
```

**验证方法**:
1. 所有测试用例运行完成
2. 检查测试报告
3. 统计通过率
4. 确认无回归

---

## rodski-demo 开发需求

**需要开发**: T15-001 ~ T15-011  
**rodski 开发**: 无（仅扩展 demo 项目）

---

## 验收总结

| 验收项 | 状态 | 备注 |
|--------|------|------|
| AC15-001 | ⏳ | 定位器类型覆盖 |
| AC15-002 | ⏳ | 关键字完整覆盖 |
| AC15-003 | ⏳ | 视觉定位功能 |
| AC15-004 | ⏳ | 桌面应用自动化 |
| AC15-005 | ⏳ | 多窗口和iframe |
| AC15-006 | ⏳ | 复杂数据引用 |
| AC15-007 | ⏳ | 负面测试集合 |
| AC15-008 | ⏳ | 功能覆盖率 |
| AC15-009 | ⏳ | 文档完整性 |
| AC15-010 | ⏳ | 完整回归测试 |

**图例**: ✅ 通过 | ❌ 失败 | ⏳ 待验证

---

## 最终目标

完成后，rodski-demo 将达到：
- **测试用例数量**: 26+ 个
- **功能覆盖率**: 90%+
- **关键字覆盖**: 16/18 (89%)
- **定位器覆盖**: 6/6 (100%)
- **高级特性覆盖**: 10/10 (100%)

成为 RodSki 框架的**完整功能展示和学习示例**。
