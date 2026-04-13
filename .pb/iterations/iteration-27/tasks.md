# Iteration 27 任务清单

**版本**: v5.5.0  
**分支**: release/v5.5.0  
**依赖**: iteration-26 完成

---

## T27-001: AGENT_INTEGRATION.md 格式统一 [0.5h]

### 改动

| 位置 | 改动 |
|------|------|
| lines 94-103 | `generate_model_xml()` 示例：`locator="vision:xxx"` → `<location>` 元素生成 |
| lines 382-408 | 视觉定位集成示例：`locator=f"vision:{desc}"` → `<location type="vision">` 生成 |
| 全文检查 | 确保无 `locator=` 属性引用 |

### 验证

```bash
grep 'locator=' rodski/docs/AGENT_INTEGRATION.md
# 应返回零结果
```

---

## T27-002: VISION_LOCATION.md 格式统一 [1h]

### 改动

| 位置 | 改动 |
|------|------|
| lines 21-39 | 定位器格式说明：`locator="vision:xxx"` → `<location type="vision">` |
| lines 38 | 删除"使用 locator 属性"约束描述 |
| line 51 | 核心流程说明更新 |
| lines 109-139 | Web/Desktop 示例全部重写为 `<location>` 格式 |
| line 215 | 约束描述更新 |

### 验证

```bash
grep 'locator=' rodski/docs/VISION_LOCATION.md
# 应返回零结果
```

---

## T27-003: TEST_CASE_WRITING_GUIDE.md 格式统一 [0.5h]

### 改动

| 位置 | 改动 |
|------|------|
| lines 1099-1207 | 第 11 节"视觉定位"示例全部改为 `<location>` 格式 |
| 全文检查 | 确保无 `locator=` 属性示例 |

### 验证

```bash
grep 'locator=' rodski/docs/TEST_CASE_WRITING_GUIDE.md
# 应返回零结果
```

---

## T27-004: CORE_DESIGN_CONSTRAINTS.md 格式统一 [0.3h]

### 改动

| 位置 | 改动 |
|------|------|
| line 194 附近 | 简化格式 `<element name="..." type="id" value="..."/>` 标记为 **已移除** |
| 全文检查 | 确保只展示 `<location>` 作为唯一正确格式 |

---

## T27-005: ADVANCED_TIPS.md 格式统一 [0.3h]

### 改动

| 位置 | 改动 |
|------|------|
| lines 55-108 | 删除"单定位器（传统写法）"整节或标记为 **已移除** |
| 对比总结表 | 更新为只推荐 `<location>` 多定位器格式 |

---

## T27-006: 其他文档检查 [0.4h]

### 检查并修正

| 文档 | 检查内容 |
|------|---------|
| `rodski/docs/SKILL_REFERENCE.md` | 确保无 `locator=` 引用 |
| `rodski/docs/API_REFERENCE.md` | 确保无 `locator=` 引用 |
| `rodski/docs/DATA_FILE_ORGANIZATION.md` | 确保无旧格式 |
| `rodski/docs/DB_DRIVER_SUPPORT.md` | 确保无旧格式 |

---

## T27-007: 移除文档中所有 Excel 引用 [0.5h]

### 改动文件

| 文件 | 改动 |
|------|------|
| `README.md` | `rodski run case.xlsx` → `rodski run case/` |
| `rodski/docs/ARCHITECTURE.md` | 移除 Excel 文件结构图（lines 228-249）、`excel_parser.py` 引用（line 49）、CLI .xlsx 示例（lines 573-588）、"Excel结果回填"描述（line 31） |
| `rodski/docs/TEST_CASE_WRITING_GUIDE.md` | Excel 映射节（lines 75-85）标记为历史或删除 |
| `rodski/docs/json_support_design.md` | "Excel 数据表" → "XML 数据表" |

### 验证

```bash
grep -ri "excel\|\.xlsx" rodski/docs/ README.md
# 应返回零结果
```

---

## T27-008: 全文档审计 [0.5h]

### 验证

```bash
# 定位器格式审计
grep -r 'locator="' rodski/docs/ --include="*.md"
# 应返回零结果

# Excel 引用审计
grep -ri 'excel\|\.xlsx' rodski/docs/ README.md
# 应返回零结果

# 简化格式审计
grep -r 'type="id" value=' rodski/docs/ --include="*.md"
# 应返回零结果（排除"已移除"标注上下文）
```

---

## 执行顺序

```
T27-001 ~ T27-006 (定位器格式统一，可并行)
    ↓
T27-007 (Excel 移除)
    ↓
T27-008 (全文档审计)
```

## 工时估算

| 任务 | 预估 |
|------|------|
| T27-001 | 0.5h |
| T27-002 | 1.0h |
| T27-003 | 0.5h |
| T27-004 | 0.3h |
| T27-005 | 0.3h |
| T27-006 | 0.4h |
| T27-007 | 0.5h |
| T27-008 | 0.5h |
| **合计** | **4h** |
