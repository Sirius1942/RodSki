# RodSki 代码和文档精简建议

**分析日期**: 2026-03-27
**项目规模**: 114个Python文件，33个文档，总大小48MB

---

## 一、可删除的重复/过时文档

### 1. 视觉定位相关（已整合到核心文档）

**可删除**：
- `docs/design/LLM_VISION_LOCATOR_DESIGN.md` (615行) - 已被 `VISION_LOCATION.md` 取代
- `docs/design/PC_AUTOMATION_ENHANCEMENT.md` (388行) - 违反核心约束，已废弃
- `docs/design/RPA_GAP_ANALYSIS.md` (175行) - 分析文档，已完成开发
- `docs/design/RPA_ROADMAP_SUMMARY.md` - 规划文档，已完成

**原因**：
- 视觉定位已在 `核心设计约束.md` 第10章和 `VISION_LOCATION.md` 中完整描述
- PC_AUTOMATION_ENHANCEMENT 设计违反了核心约束（新增关键字），已按新约束重新实现
- 分析和规划文档在开发完成后可归档

**节省**: ~1200行文档

---

## 二、可合并的文档

### 1. Agent 相关文档

**当前**：
- `docs/agent-guides/AGENT_SKILL_GUIDE.md` (213行)
- `docs/design/AGENT_AUTOMATION_DESIGN.md` (263行)

**建议**: 合并为一个 `AGENT_GUIDE.md`，删除重复内容

**节省**: ~100行

---

## 三、可精简的代码

### 1. 遗留 Excel 解析代码（已标记废弃）

**可删除**：
- `core/data_parser.py` - 遗留 Excel 解析，已有废弃标记
- `data/excel_parser.py` - 遗留 Excel 解析器

**前提**: 确认所有用例已迁移到 XML 格式

**节省**: ~500行代码

**注意**: 需先确认以下文件不再使用 Excel 解析：
- `rodski/ui/main_window.py`
- `rodski/core/keyword_engine.py`
- 相关测试文件

---

## 四、可归档的规划文档

### 1. 已完成的规划和分析

**可移至 archive/ 目录**：
- `docs/design/RPA_ROADMAP_SUMMARY.md` (90行) - 路线图已完成
- `docs/design/RPA_GAP_ANALYSIS.md` (175行) - 差距分析已完成
- `docs/requirements/RODSKI_REQUIREMENTS_HISTORY_2026-03-20.md` - 历史需求

**原因**: 这些文档记录了历史决策，有参考价值但不属于当前活跃文档

**节省**: 主文档目录减少 ~265行

---

## 五、重复的 API Key 配置

### 1. 全局变量文件重复

**当前**：
- `rodski-demo/DEMO/vision_web/data/globalvalue.xml` - 包含相同的 API 配置
- `rodski-demo/DEMO/vision_desktop/data/globalvalue.xml` - 包含相同的 API 配置

**建议**:
- 创建模板文件 `globalvalue.xml.template`
- 实际配置文件加入 `.gitignore`
- 避免提交真实 API Key

**安全性提升**: 防止 API Key 泄露

---

## 六、测试文件精简

### 1. 遗留 Excel 相关测试

**可删除**（如果确认 Excel 解析已废弃）：
- `tests/unit/test_excel_parser.py`
- `tests/unit/test_edge_cases.py` (部分 Excel 测试)
- `tests/integration/test_end_to_end.py` (部分 Excel 测试)
- `tests/test_data_parser.py`

**节省**: ~300-400行测试代码

---

## 七、临时和开发文件

### 1. Spec 文件（已完成的任务）

**可删除**：
- `.kiro/specs/rodski-doc-code-audit/` 目录下所有文件
  - `agent-capability-gap-analysis.md`
  - `agent-guide-plan.md`
  - `vision-location-design-v2.md`
  - `vision-location-tasks-v2.md`
  - `vision-location-tasks-v3.md`
  - `vision-location-tasks.md`
  - `vision-tasks-review.md`

**原因**: 这些是开发过程中的临时规划文件，任务已完成

**节省**: 清理开发临时文件

---

## 八、执行建议

### 优先级 1 - 立即可执行（低风险）

1. **删除临时 spec 文件**
   ```bash
   rm -rf .kiro/specs/rodski-doc-code-audit/
   ```

2. **创建 API Key 模板并清理敏感信息**
   ```bash
   cp rodski-demo/DEMO/vision_web/data/globalvalue.xml \
      rodski-demo/DEMO/vision_web/data/globalvalue.xml.template
   # 手动替换真实 key 为占位符
   echo "rodski-demo/**/globalvalue.xml" >> .gitignore
   ```

3. **归档历史文档**
   ```bash
   mkdir -p rodski/docs/archive
   mv rodski/docs/design/RPA_*.md rodski/docs/archive/
   mv rodski/docs/requirements/*HISTORY*.md rodski/docs/archive/
   ```

### 优先级 2 - 需确认后执行（中风险）

4. **删除过时设计文档**（确认已被新文档取代）
   - `docs/design/LLM_VISION_LOCATOR_DESIGN.md` → 已被 `VISION_LOCATION.md` 取代
   - `docs/design/PC_AUTOMATION_ENHANCEMENT.md` → 违反核心约束，已废弃

5. **合并 Agent 文档**
   - 合并 `AGENT_SKILL_GUIDE.md` 和 `AGENT_AUTOMATION_DESIGN.md`

### 优先级 3 - 需全面测试后执行（高风险）

6. **删除 Excel 解析代码**（需先确认所有用例已迁移到 XML）
   ```bash
   # 1. 搜索所有 Excel 引用
   grep -r "excel_parser\|ExcelParser" rodski/ --include="*.py"

   # 2. 确认无引用后删除
   rm rodski/core/data_parser.py
   rm rodski/data/excel_parser.py
   rm tests/unit/test_excel_parser.py
   rm tests/test_data_parser.py
   ```

---

## 九、预期收益

| 类别 | 节省量 | 说明 |
|------|--------|------|
| 文档 | ~1,500行 | 删除重复/过时设计文档 |
| 代码 | ~500行 | 删除遗留 Excel 解析 |
| 测试 | ~400行 | 删除 Excel 相关测试 |
| 临时文件 | 7个文件 | 清理 spec 开发文件 |
| **总计** | **~2,400行 + 7文件** | **代码库精简约 5%** |

---

## 十、风险提示

⚠️ **执行前必须**：
1. 创建 Git 分支进行清理工作
2. 运行完整测试套件确认无破坏性影响
3. 确认 Excel 解析代码确实无引用
4. 备份重要文档到 archive/ 而非直接删除

---

**分析完成日期**: 2026-03-27
**建议执行周期**: 1-2周内完成优先级1和2，优先级3需充分测试

