# Iteration 17: 关键字覆盖 + 视觉定位

**版本**: v4.9.0  
**分支**: release/v4.9.0  
**日期**: 2026-04-09  
**工时**: 4h  
**优先级**: P0  
**前置依赖**: iteration-16

---

## 目标

补充关键字覆盖和视觉定位功能：
1. 创建 TC017 关键字完整覆盖测试
2. 创建 TC018 视觉定位功能测试（可选）

---

## 任务清单

### T17-001: TC017 关键字完整覆盖测试 (2.5h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc017_keywords.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/KeywordTest.xml`
- `rodski-demo/DEMO/demo_full/data/KeywordTest_verify.xml`

**任务**:
创建测试用例 TC017，覆盖：
- wait (等待)
- clear (清空输入)
- screenshot (截图)
- assert (断言)
- upload_file (文件上传)

**验收**:
- 所有关键字都能正常执行
- wait 等待时间正确
- clear 清空输入成功
- screenshot 生成截图文件
- assert 断言正确
- upload_file 上传文件成功

---

### T17-002: TC018 视觉定位功能测试 (1.5h)

**文件**: 
- `rodski-demo/DEMO/demo_full/case/tc018_vision.xml`
- `rodski-demo/DEMO/demo_full/model/model.xml`
- `rodski-demo/DEMO/demo_full/data/VisionLogin.xml`

**任务**:
1. 创建测试用例 TC018
2. 添加视觉定位模型：
   - VisionLogin (使用 vision 语义定位)
   - VisionCoordinate (使用 vision_bbox 坐标定位)
3. 添加测试数据
4. 添加说明文档，标注需要 OmniParser 服务

**验收**:
- 模型定义正确
- 测试用例结构完整
- 文档说明清晰
- 有 OmniParser 服务时可以运行

---

## 验收标准

- [ ] TC017 测试通过
- [ ] TC018 模型定义完整
- [ ] 关键字覆盖率提升
- [ ] 所有测试用例通过
- [ ] 无回归问题

---

## 工作流程

1. 确认 iteration-16 已完成
2. 创建分支: `git checkout -b release/v4.9.0`
3. 执行 T17-001
4. 执行 T17-002
5. 运行回归测试
6. 更新 record.md
7. 合并到 main: `git merge release/v4.9.0`
8. 打标签: `git tag v4.9.0`

---

## 参考文档

- `.pb/iterations/iteration-14-19-plan.md` - 总体规划
- `rodski/docs/SKILL_REFERENCE.md` - 关键字参考
- `rodski/docs/VISION_LOCATION.md` - 视觉定位设计
