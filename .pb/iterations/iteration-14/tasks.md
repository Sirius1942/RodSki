# Iteration 14 任务清单

## 任务汇总

| 任务 | 内容 | 预计 | 状态 | 负责人 |
|------|------|------|------|--------|
| T14-001 | 添加 expect_fail 属性 | 0.5h | 待开始 | - |
| T14-002 | 修复 run_demo.sh 路径 | 0.5h | 待开始 | - |
| T14-003 | 补充 tc_expect_fail.xml | 2h | 待开始 | - |

**总计**: 3h

---

## T14-001: 添加 expect_fail 属性

**预计**: 0.5h  
**文件**: `rodski-demo/DEMO/demo_full/case/demo_case.xml`

### 步骤
1. 找到 TC012A 用例定义
2. 添加 `expect_fail="是"` 属性
3. 找到 TC014A 用例定义
4. 添加 `expect_fail="是"` 属性
5. 运行测试验证

### 验收
- [ ] TC012A 有 expect_fail 属性
- [ ] TC014A 有 expect_fail 属性
- [ ] 测试报告显示"预期失败"

---

## T14-002: 修复 run_demo.sh 路径

**预计**: 0.5h  
**文件**: `rodski-demo/DEMO/demo_full/run_demo.sh`

### 步骤
1. 打开 run_demo.sh
2. 修正第 36 行路径
3. 修正第 30 行路径
4. 测试脚本运行

### 验收
- [ ] 第 36 行路径正确
- [ ] 第 30 行路径正确
- [ ] 脚本可以运行
- [ ] 可以找到测试报告

---

## T14-003: 补充 tc_expect_fail.xml

**预计**: 2h  
**文件**: 多个文件

### 步骤
1. 在 model.xml 添加 ErrorMessage 模型
   ```xml
   <model name="ErrorMessage" type="ui" servicename="">
       <element name="errorMsg" type="text">
           <location type="id">errorMessage</location>
       </element>
   </model>
   ```

2. 在 LoginForm.xml 添加 L002 数据
   ```xml
   <row id="L002">
       <field name="username">admin</field>
       <field name="password">wrongpassword</field>
       <field name="loginBtn">click</field>
   </row>
   ```

3. 创建 ErrorMessage_verify.xml
   ```xml
   <datatable name="ErrorMessage_verify">
       <row id="V001">
           <field name="errorMsg">用户名或密码错误</field>
       </row>
   </datatable>
   ```

4. 扩展 demosite/app.py
   - 修改 /login 路由
   - 添加错误提示逻辑
   - 返回错误消息

5. 运行 tc_expect_fail.xml 测试

### 验收
- [ ] ErrorMessage 模型已添加
- [ ] L002 数据已添加
- [ ] ErrorMessage_verify.xml 已创建
- [ ] demosite 支持错误提示
- [ ] tc_expect_fail.xml 可以运行
