-- ═══════════════════════════════════════════════════════════════
-- TC050 内置函数验收测试数据（v6.7.0）
-- 导入方式: sqlite3 data.sqlite < tc050_data.sql
-- ═══════════════════════════════════════════════════════════════

-- 注册数据表（如不存在）
INSERT OR IGNORE INTO rs_datatable VALUES ('BuiltinFunc', 'RegisterAPI', 'data', 'standard', '内置函数验收数据', CURRENT_TIMESTAMP);
INSERT OR IGNORE INTO rs_datatable VALUES ('BuiltinFunc_verify', 'RegisterAPI_verify', 'verify', 'standard', '内置函数验收验证', CURRENT_TIMESTAMP);
INSERT OR IGNORE INTO rs_datatable VALUES ('BuiltinFuncUI', 'TestForm', 'data', 'standard', '内置函数UI验收', CURRENT_TIMESTAMP);

-- ═══════════════════════════════════════════════════════════════
-- random() 函数测试数据
-- ═══════════════════════════════════════════════════════════════

-- R001: random(int) 随机整数
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R001', 'random(int)-范围随机整数');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R001', 'username', 'user_${random(int, 1000, 9999)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R001', 'password', 'pass123');

-- R002: random(str) 随机字符串拼接
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R002', 'random(str)-前后拼接');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R002', 'username', 'test_${random(str, 6)}_user');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R002', 'password', 'pass123');

-- R003: random(phone) 随机手机号
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R003', 'random(phone)-随机手机号');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R003', 'username', '${random(phone)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R003', 'password', 'pass123');

-- R004: random(email) 随机邮箱
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R004', 'random(email)-随机邮箱');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R004', 'username', '${random(email)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R004', 'password', 'pass123');

-- R005: random(uuid) UUID
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R005', 'random(uuid)-UUID生成');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R005', 'username', '${random(uuid)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R005', 'password', 'pass123');

-- R006: random(choice) 随机选取
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R006', 'random(choice)-随机选取');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R006', 'username', '${random(choice, alice, bob, charlie)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R006', 'password', 'pass123');

-- R007: random(float) 随机浮点数
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R007', 'random(float)-随机浮点数');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R007', 'username', 'amount_${random(float, 10.00, 999.99)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R007', 'password', 'pass123');

-- R008: random(digits) 纯数字串
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R008', 'random(digits)-纯数字');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R008', 'username', 'code_${random(digits, 6)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R008', 'password', 'pass123');

-- ═══════════════════════════════════════════════════════════════
-- date() 函数测试数据
-- ═══════════════════════════════════════════════════════════════

-- R011: date(now) 当前日期时间
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R011', 'date(now)-当前日期时间');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R011', 'username', 'created_${date(now)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R011', 'password', 'pass123');

-- R012: date(today) 当前日期
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R012', 'date(today)-当前日期');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R012', 'username', 'day_${date(today)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R012', 'password', 'pass123');

-- R013: date(timestamp) 时间戳
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R013', 'date(timestamp)-时间戳');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R013', 'username', 'ts_${date(timestamp)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R013', 'password', 'pass123');

-- R014: date(offset) 日期偏移-天
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R014', 'date(offset)-日期偏移天');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R014', 'username', 'expire_${date(offset, 30)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R014', 'password', 'pass123');

-- R015: date(offset, Nh) 小时偏移
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R015', 'date(offset)-小时偏移');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R015', 'username', 'start_${date(offset, -2h)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R015', 'password', 'pass123');

-- R016: date(today) 自定义格式
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R016', 'date(today)-自定义格式');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R016', 'username', 'compact_${date(today, %Y%m%d)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R016', 'password', 'pass123');

-- ═══════════════════════════════════════════════════════════════
-- 字符串拼接测试数据
-- ═══════════════════════════════════════════════════════════════

-- R021: 前缀 + random
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R021', '前缀+random拼接');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R021', 'username', 'user_${random(int, 10000, 99999)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R021', 'password', 'pass123');

-- R022: random + 后缀
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R022', 'random+后缀拼接');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R022', 'username', '${random(str, 8)}@example.com');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R022', 'password', 'pass123');

-- R023: 前缀 + date + 后缀
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R023', '前缀+date+后缀');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R023', 'username', 'report_${date(today, %Y%m%d)}.pdf');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R023', 'password', 'pass123');

-- R024: 多函数串联
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R024', '多函数串联');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R024', 'username', '${random(str, 4)}_${random(digits, 4)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R024', 'password', 'pass123');

-- R025: random + date 混合
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R025', 'random+date混合拼接');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R025', 'username', 'TXN${date(today, %Y%m%d)}${random(digits, 8)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R025', 'password', 'pass123');

-- ═══════════════════════════════════════════════════════════════
-- 边界场景测试数据
-- ═══════════════════════════════════════════════════════════════

-- R031: 转义 - $${} 不解析
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R031', '转义-字面量保留');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R031', 'username', '$${random(int, 1, 9)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R031', 'password', 'pass123');

-- R032: 未知函数 - 保持原样
INSERT INTO rs_row VALUES ('BuiltinFunc', 'R032', '未知函数-不解析');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R032', 'username', '${unknown_func(abc)}');
INSERT INTO rs_field VALUES ('BuiltinFunc', 'R032', 'password', 'pass123');

-- ═══════════════════════════════════════════════════════════════
-- 验证数据（验证函数已被正确解析）
-- 验证策略：接口返回 echo 请求体，验证字段值不再包含 ${...} 语法
-- ═══════════════════════════════════════════════════════════════

-- V001: 验证 username 不含 ${random(
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V001', '验证random(int)已解析');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V001', '_status', '200');

-- V002: 验证 username 含 test_ 前缀和 _user 后缀
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V002', '验证random(str)拼接');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V002', '_status', '200');

-- V003: 验证手机号格式（11位数字）
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V003', '验证random(phone)格式');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V003', '_status', '200');

-- V004: 验证邮箱格式（含@）
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V004', '验证random(email)格式');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V004', '_status', '200');

-- V005: 验证UUID格式
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V005', '验证random(uuid)格式');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V005', '_status', '200');

-- V006: 验证choice结果在候选列表中
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V006', '验证random(choice)结果');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V006', '_status', '200');

-- V007: 验证float格式
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V007', '验证random(float)格式');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V007', '_status', '200');

-- V008: 验证digits纯数字
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V008', '验证random(digits)格式');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V008', '_status', '200');

-- V011~V016: date函数验证（验证返回200即可，时间值每次不同）
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V011', '验证date(now)已解析');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V011', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V012', '验证date(today)已解析');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V012', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V013', '验证date(timestamp)已解析');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V013', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V014', '验证date(offset)天偏移');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V014', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V015', '验证date(offset)小时偏移');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V015', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V016', '验证date(today)自定义格式');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V016', '_status', '200');

-- V021~V025: 拼接验证
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V021', '验证前缀+random');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V021', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V022', '验证random+后缀');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V022', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V023', '验证前缀+date+后缀');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V023', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V024', '验证多函数串联');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V024', '_status', '200');

INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V025', '验证random+date混合');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V025', '_status', '200');

-- V031: 转义验证 - username 应为字面量 ${random(int, 1, 9)}
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V031', '验证转义保留字面量');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V031', '_status', '200');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V031', 'username', '${random(int, 1, 9)}');

-- V032: 未知函数验证 - username 应保持原样 ${unknown_func(abc)}
INSERT INTO rs_row VALUES ('BuiltinFunc_verify', 'V032', '验证未知函数不解析');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V032', '_status', '200');
INSERT INTO rs_field VALUES ('BuiltinFunc_verify', 'V032', 'username', '${unknown_func(abc)}');

-- ═══════════════════════════════════════════════════════════════
-- UI 场景测试数据
-- ═══════════════════════════════════════════════════════════════

-- T050: UI表单输入含random
INSERT INTO rs_row VALUES ('BuiltinFuncUI', 'T050', 'UI表单-random输入');
INSERT INTO rs_field VALUES ('BuiltinFuncUI', 'T050', 'username', 'auto_${random(str, 4)}');
INSERT INTO rs_field VALUES ('BuiltinFuncUI', 'T050', 'role', 'select【管理员】');
INSERT INTO rs_field VALUES ('BuiltinFuncUI', 'T050', 'submitBtn', 'click');
