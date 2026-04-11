# RodSki v5.3.1 测试用例验证报告

> 测试日期: 2026-04-11
> 分支: fix/v5.3.1-validation
> 结果来源: rodski-demo/ 最新运行结果

---

## 一、汇总

| 测试套件 | 总数 | 通过 | 失败 | 跳过 | 通过率 |
|---------|------|------|------|------|--------|
| demo_full 主用例 (TC001-TC015) | 19 | 19 | 0 | 0 | 100% |
| demo_full 扩展用例 (TC016-TC024, TC_EF) | 10 | 8 | 2 | 2 | 80% (不含跳过) |
| 独立DB用例 (TC020-TC024) | 5 | 3 | 0 | 2 | 100% (不含跳过) |
| 独立数据引用 (TC025-TC027) | 3 | 2 | 1 | 0 | 66.7% |
| 独立脚本用例 (TC028-TC030) | 3 | 3 | 0 | 0 | 100% |
| 运行时控制 (RT_INSERT) | 1 | 1 | 0 | 0 | 100% |
| 视觉Web (web_001) | 1 | 0 | 1 | 0 | 0% |
| 视觉桌面 (desktop_001) | 1 | 0 | 0 | 1 | N/A |

---

## 二、demo_full 主用例 (demo_case.xml)

结果文件: `DEMO/demo_full/result/rodski_20260411_115851/result.xml` — **19/19 PASS (100%)**

### TC001 — Web登录测试
- **类型**: 界面
- **步骤**:
  1. `navigate` → http://localhost:8000
  2. `type` LoginForm L001 → 输入 admin/123456 + click 登录
  3. `close` 关闭浏览器
- **校验项**: 无显式 verify（登录动作完成即通过）
- **结果**: PASS (1.92s)
- **核对**: [ ]

### TC002 — 看板数据验证
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录
  2. `verify` Dashboard V001 → 验证 totalOrders=3, completedOrders=2
  3. `close`
- **校验项**: Dashboard.totalOrders=3, Dashboard.completedOrders=2
- **结果**: PASS (2.49s)
- **核对**: [ ]

### TC003 — 功能测试页操作
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + NavMenu N001 跳转测试页
  2. `type` TestForm T001 → 输入"功能测试输入" + select选项2 + click
  3. `verify` TestForm V001 → 验证 result=测试成功
  4. `close`
- **校验项**: TestForm.result=测试成功
- **结果**: PASS (3.58s)
- **核对**: [ ]

### TC004 — API登录接口测试
- **类型**: 接口
- **步骤**:
  1. `send` LoginAPI D001 → POST 登录请求 (admin/123456)
  2. `verify` LoginAPI V001 → 验证响应
- **校验项**: success=true, token=demo_token_123
- **结果**: PASS (1.12s)
- **核对**: [ ]

### TC005 — API查询订单
- **类型**: 接口
- **步骤**:
  1. `send` OrderAPI D001 → 查询订单 ORD001
  2. `verify` OrderAPI V001 → 验证响应
- **校验项**: status=success
- **结果**: PASS (1.11s)
- **核对**: [ ]

### TC006 — 数据库查询订单
- **类型**: 数据库
- **步骤**:
  1. `DB` QuerySQL Q001 → list 查询前3行
  2. `DB` QuerySQL Q002 → insert 插入测试订单
- **校验项**: 无显式 verify（SQL执行成功即通过）
- **结果**: PASS (1.09s)
- **备注**: 早期运行曾因 orders 表不存在/NOT NULL 约束失败，后修复 DB 初始化后通过
- **核对**: [ ]

### TC007 — 代码生成测试数据
- **类型**: 界面
- **步骤**:
  1. `run` data_gen/gen_data.py → 执行 Python 脚本
- **校验项**: 无显式 verify（脚本执行无异常即通过）
- **结果**: PASS (0.56s)
- **核对**: [ ]

### TC008 — UI动作关键字测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` UIActions A001 → click + 输入"测试输入"
  3. `verify` UIActions V001 → 验证结果
- **校验项**: result=操作成功
- **结果**: PASS (3.62s)
- **核对**: [ ]

### TC009 — Return引用测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` ReturnTest R001 → 输入测试值1/测试值2
  3. `get` #username → 获取元素文本
  4. `verify` ReturnTest V001 → 验证 result=${Return[-1]}
- **校验项**: result 等于最近 Return 值
- **结果**: PASS (4.14s)
- **核对**: [ ]

### TC009A — history连续性测试
- **类型**: 界面
- **步骤**:
  1. `navigate` → http://localhost:8000
  2. `type` LoginForm L001 → 登录
  3. `verify` Dashboard V001 → 看板验证
  4. `close`
- **校验项**: totalOrders=3, completedOrders=2
- **结果**: PASS (2.47s)
- **核对**: [ ]

### TC010 — set/get命名访问测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` TestForm T001 → 提交表单
  3. `set` first_result=${Return[-1]} → 保存返回值
  4. `type` TestForm T002 → 再次提交
  5. `set` second_result=${Return[-1]} → 保存第二次返回值
  6. `get` first_result → 读取第一次保存的值
  7. `verify` SetGetVerify V001 → 验证读取值
- **校验项**: value=${Return[-1]}（验证 get 读回的值正确）
- **结果**: PASS (5.86s)
- **核对**: [ ]

### TC011 — get选择器模式测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` TestForm T001 → 提交表单
  3. `get` #formResult → CSS 选择器获取元素文本
  4. `verify` GetVerify V001 → 验证
- **校验项**: result=${Return[-1]}
- **结果**: PASS (4.14s)
- **核对**: [ ]

### TC012 — evaluate结构化返回测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate → http://localhost:8000
  2. `evaluate` () => ({title: document.title}) → 执行 JS
  3. `verify` EvaluateResult V001 → 验证返回对象
  4. `close`
- **校验项**: title=${Return[-1].title}
- **结果**: PASS (2.50s)
- **核对**: [ ]

### TC012A — get不存在key报错测试
- **类型**: 界面 | **expect_fail=是**
- **步骤**:
  1. `get` undefined_key → 获取不存在的命名变量
- **校验项**: 预期失败，验证错误信息 "[SKI312] 命名变量 'undefined_key' 不存在"
- **结果**: PASS (0.04s) — 预期失败，实际失败，判定通过
- **核对**: [ ]

### TC012B — get模型模式测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` TestForm T001 → 提交表单
  3. `get` GetModel G001 → 模型模式读取 formResult
  4. `verify` GetModelVerify V001 → 验证 dict 返回
- **校验项**: formResult=${Return[-1].formResult}
- **结果**: PASS (4.18s)
- **核对**: [ ]

### TC013 — type Auto Capture测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` DemoForm F001 → 输入 testuser + click 提交
  3. `verify` DemoFormVerify V001 → 验证 auto_capture
- **校验项**: resultId=${Return[-1].resultId}
- **结果**: PASS (3.64s)
- **核对**: [ ]

### TC014 — send Auto Capture测试
- **类型**: 接口
- **步骤**:
  1. `send` LoginAPICapture D001 → 发送登录请求
  2. `verify` LoginAPICapture V001 → 验证 auto_capture
- **校验项**: data.token=${Return[-1]._capture.token}
- **结果**: PASS (1.10s)
- **核对**: [ ]

### TC014A — type Auto Capture失败测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` DemoFormBadCapture F001 → 触发错误 auto_capture
  3. `close`
- **校验项**: 无显式 verify（capture 逻辑测试）
- **结果**: PASS (33.11s)
- **核对**: [ ]

### TC015 — 结构化日志验证
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `type` DemoForm F001 → 提交表单
  3. `set` saved_id=${Return[-1].resultId} → 保存 resultId
  4. `get` saved_id → 读取
  5. `close`
- **校验项**: set/get 链路完成无异常
- **结果**: PASS (4.21s)
- **核对**: [ ]

---

## 三、demo_full 扩展用例

结果文件: `DEMO/demo_full/result/rodski_20260411_082656/result.xml` (全量29用例) + 后续单独运行

### TC016 — 定位器类型覆盖测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate → http://localhost:8000/locator-test
  2. `type` + `verify` LocatorTest_ID → ID 定位器
  3. `type` + `verify` LocatorTest_Name → Name 定位器
  4. `type` + `verify` LocatorTest_CSS → CSS 定位器
  5. `type` + `verify` LocatorTest_XPath → XPath 定位器
  6. `close`
- **校验项**: 4种定位器各自验证 result 字段
- **结果**: **FAIL** — 元素 id=input_by_id 未找到（/locator-test 页面不存在）
- **失败原因**: demosite 未提供 /locator-test 路由
- **核对**: [ ]

### TC017 — 关键字完整覆盖测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate + 登录 + 跳转测试页
  2. `wait` 2s
  3. `screenshot` tc017_test.png
  4. `type` + `clear` #username → 输入后清空
  5. `type` + `verify` KeywordTest → 再次输入并验证
  6. `get` #formResult + `verify` → 获取并验证文本
  7. `close`
- **校验项**: formResult="提交成功: 关键字测试内容", formResult=${Return[-1]}
- **结果**: PASS (8.54s)
- **核对**: [ ]

### TC018 — 视觉定位功能测试
- **类型**: 界面 | **execute=否** (需要 OmniParser 服务)
- **步骤**:
  1. [前置] navigate → http://localhost:8000
  2. `type` VisionLogin L001 → vision 语义定位登录
  3. `type` VisionCoordinate C001 → vision_bbox 坐标定位
  4. `verify` VisionCoordinate V001 → 验证坐标定位结果
  5. `close`
- **校验项**: formResult="提交成功: 坐标定位测试"
- **结果**: **跳过**（execute=否）
- **核对**: [ ]

### TC019 — 桌面应用自动化测试
- **类型**: 界面 | **execute=否** (需要桌面环境)
- **步骤**:
  1. `wait` 2s（等待应用启动，launch 已注释）
  2. `run` type_text.py Hello_RodSki → 输入文本
  3. `run` key_combo.py ctrl+a → 全选
  4. `run` key_combo.py ctrl+c → 复制
- **校验项**: 无显式 verify
- **结果**: **跳过**（execute=否）
- **核对**: [ ]

### TC020 — 多窗口和iframe测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate → http://localhost:8000
  2. `wait` 1s（多窗口/iframe 步骤已注释，仅骨架）
  3. `close`
- **校验项**: 无（步骤已注释，当前仅验证框架不报错）
- **结果**: PASS (2.21s)
- **核对**: [ ]

### TC021 — 复杂数据引用测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate GlobalValue.DefaultValue.URL + 登录 + 跳转测试页
  2. `type` TestForm T001 → 提交表单
  3. `get` TestForm.formResult + `set` savedResult → 获取并保存
  4. `get` savedResult + `verify` TestForm V001 → 读取变量并验证
  5. `get` TestForm.formResult + `set` finalResult + `get` finalResult → 嵌套引用
  6. `close`
- **校验项**: TestForm.result=测试成功（通过 set/get 链路）
- **结果**: PASS (7.06s)
- **核对**: [ ]

### TC022 — 元素不存在测试
- **类型**: 界面 | **expect_fail=是**
- **步骤**:
  1. `navigate` → http://localhost:8000
  2. `wait` 1s
  3. `type` NonExistentModel E001 → 操作不存在的元素
  4. `close`
- **校验项**: 预期失败，验证 "[SKI302] 元素未找到 id=thisElementDoesNotExist"
- **结果**: PASS (20.23s) — 预期失败，实际失败，判定通过
- **核对**: [ ]

### TC023 — 接口错误响应测试
- **类型**: 接口 | **expect_fail=是**
- **步骤**:
  1. `send` ErrorAPI E001 → 调用不存在的 API
  2. `get` nonexistent_variable_that_does_not_exist → 访问不存在变量
- **校验项**: 预期失败，验证 "[SKI312] 命名变量不存在"
- **结果**: PASS (0.55s) — 预期失败，实际失败，判定通过
- **核对**: [ ]

### TC024 — SQL语法错误测试
- **类型**: 数据库 | **expect_fail=是**
- **步骤**:
  1. `DB` ErrorSQL E001 → 执行语法错误的 SQL
- **校验项**: 预期失败，验证 "syntax error"
- **结果**: PASS (0.003s) — 预期失败，实际失败，判定通过
- **核对**: [ ]

### TC_EF001 — 非法登录测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate → http://localhost:8000
  2. `type` LoginForm L002 → 输入 admin/wrongpassword + click
  3. `verify` ErrorMessage V001 → 验证错误提示
  4. `close`
- **校验项**: errorMsg="用户名或密码错误"
- **结果**: PASS (2.53s)
- **核对**: [ ]

### TC_EF002 — 正常登录测试
- **类型**: 界面
- **步骤**:
  1. [前置] navigate → http://localhost:8000
  2. `type` LoginForm L001 → 正确登录
  3. `verify` Dashboard V001 → 验证看板
  4. `close`
- **校验项**: totalOrders=3, completedOrders=2
- **结果**: PASS (2.51s)
- **核对**: [ ]

---

## 四、独立数据库用例 (case/tc_database.xml)

结果文件: `result/rodski_20260411_115541/result.xml` — **3/3 PASS (100%)**

### TC020(DB) — SQLite查询订单
- **类型**: 数据库
- **步骤**:
  1. `DB` QuerySQL Q001 → list 查询前3行
  2. `verify` QuerySQL V001 → 验证 order_no=${Return[-1][0].order_no}
- **校验项**: 查询结果非空，order_no 存在
- **结果**: PASS (1.08s)
- **核对**: [ ]

### TC021(DB) — SQLite插入并验证
- **类型**: 数据库
- **步骤**:
  1. `DB` QuerySQL Q002 → insert 测试订单 TEST001
  2. `DB` QuerySQL Q003 → get_by_id 查询 TEST001
  3. `verify` QuerySQL V002 → 验证字段
- **校验项**: order_no=TEST001, customer_name=测试用户, total_amount=999.00
- **结果**: PASS (1.64s)
- **核对**: [ ]

### TC022(DB) — SQLite聚合查询
- **类型**: 数据库
- **步骤**:
  1. `DB` QuerySQL Q004 → COUNT(*) 统计
  2. `verify` QuerySQL V003 → 验证统计值
- **校验项**: total=${Return[-1][0].total}
- **结果**: PASS (1.07s)
- **核对**: [ ]

### TC023(DB) — MySQL查询订单
- **类型**: 数据库 | **execute=否** (需要 MySQL 容器)
- **结果**: **跳过**
- **核对**: [ ]

### TC024(DB) — MySQL插入并验证
- **类型**: 数据库 | **execute=否** (需要 MySQL 容器)
- **结果**: **跳过**
- **核对**: [ ]

---

## 五、独立数据引用用例 (case/tc_data_ref.xml)

结果文件: `result/rodski_20260411_115851/result.xml` — **2/3 PASS (66.7%)**

### TC025 — GlobalValue引用导航
- **类型**: 界面
- **步骤**:
  1. `navigate` GlobalValue.DefaultValue.URL → 引用全局变量导航
  2. `wait` 1s
  3. `verify` EvaluateResult V001 → 验证
  4. `close`
- **校验项**: title=${Return[-1].title}
- **结果**: PASS (2.81s)
- **核对**: [ ]

### TC026 — Return值链测试
- **类型**: 接口
- **步骤**:
  1. `send` ReturnAPI D001 → 发送接口请求
  2. `set` login_result=${Return[-1]} → 捕获返回值
  3. `get` login_result → 读取
- **校验项**: 无显式 verify（set/get 链路完成）
- **结果**: **FAIL**
- **失败原因**: `[SKI302] HTTP POST 请求失败: GlobalValue.DefaultValue.URL/api/login - Invalid URL` — model ReturnAPI 的 URL 引用未正确解析，拼成了字面字符串
- **核对**: [ ]

### TC027 — Set/Get命名变量
- **类型**: 接口
- **步骤**:
  1. `set` myvar=hello_world
  2. `set` mynum=42
  3. `get` myvar
  4. `get` mynum
- **校验项**: 无显式 verify（set/get 操作无异常即通过）
- **结果**: PASS (2.09s)
- **核对**: [ ]

---

## 六、独立脚本用例 (case/tc_script.xml)

结果文件: `result/rodski_20260411_115546/result.xml` — **3/3 PASS (100%)**

### TC028 — 运行Python脚本
- **类型**: 界面
- **步骤**:
  1. `run` data_gen/gen_data.py → 执行 Python 脚本
- **校验项**: 无显式 verify
- **结果**: PASS (0.56s)
- **核对**: [ ]

### TC029 — Evaluate JS表达式
- **类型**: 界面
- **步骤**:
  1. [前置] navigate http://localhost:8000 + wait 1s
  2. `evaluate` document.title → 执行 JS 获取标题
  3. `verify` EvaluateResult V001
  4. `close`
- **校验项**: title=${Return[-1].title}
- **结果**: PASS (3.44s)
- **核对**: [ ]

### TC030 — Wait和Screenshot
- **类型**: 界面
- **步骤**:
  1. [前置] navigate http://localhost:8000
  2. `wait` 2s
  3. `screenshot` wait_test.png
  4. `close`
- **校验项**: 无显式 verify（截图生成无异常即通过）
- **结果**: PASS (3.94s)
- **核对**: [ ]

---

## 七、DEMO 子套件

### demo_runtime_control — RT_INSERT 运行时插入步骤
结果文件: `DEMO/demo_runtime_control/result/rodski_20260411_092156/result.xml`
- **步骤**: navigate about:blank + wait 1s
- **结果**: PASS (1.68s)
- **核对**: [ ]

### vision_web — web_001 Web视觉定位演示
结果文件: `DEMO/vision_web/result/rodski_20260411_115546/result.xml`
- **步骤**: navigate baidu.com + type SearchPage S001 + verify
- **结果**: **FAIL** — vision=搜索输入框 定位失败（需要 OmniParser 服务）
- **核对**: [ ]

### vision_desktop — desktop_001 桌面视觉定位演示
- **步骤**: launch notepad + type + key_combo
- **结果**: **未执行**（需要 Windows 桌面环境）
- **核对**: [ ]

---

## 八、失败项汇总

| 用例ID | 名称 | 失败原因 | 分类 |
|--------|------|---------|------|
| TC016 | 定位器类型覆盖测试 | /locator-test 页面不存在，元素未找到 | 环境缺失 |
| TC026 | Return值链测试 | model ReturnAPI URL 未解析 GlobalValue，拼成字面字符串 | 用例/数据Bug |
| web_001 | Web视觉定位演示 | OmniParser 服务未启动，vision 定位失败 | 环境缺失 |

---

## 九、结论

1. **核心功能完备**: TC001-TC015 全部通过，覆盖 Web UI、API、DB、run、evaluate、set/get、Return引用、Auto Capture 等核心关键字
2. **数据库引擎稳定**: SQLite 查询/插入/聚合 3/3 通过；MySQL 需容器环境暂跳过
3. **负面测试有效**: expect_fail 用例 (TC012A, TC022-TC024) 均正确捕获预期错误
4. **已知失败项**:
   - TC016: 需要 demosite 增加 /locator-test 路由页面
   - TC026: ReturnAPI model 的 URL 配置需修复 GlobalValue 引用解析
   - web_001: 需启动 OmniParser 服务后重新验证
5. **脚本/高级关键字**: TC028-TC030 (run/evaluate/wait/screenshot) 全部通过
