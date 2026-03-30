# Keyword Reference

## execute

执行关键字

Args:
    keyword: 关键字名称
    params: 关键字参数
    
Returns:
    执行结果 (True/False)
    
Raises:
    UnknownKeywordError: 未知关键字
    InvalidParameterError: 参数错误
    DriverStoppedError: 驱动已停止
    RetryExhaustedError: 重试耗尽
    DriverError: 驱动操作失败

## _should_retry

检查错误是否应该重试

## _record_retry

记录重试次数

## get_retry_stats

获取重试统计

## set_retry_config

动态设置重试配置

## store_return

存储返回值

## get_return

获取返回值，支持正负索引

## _try_locators

尝试多个定位器，按 priority 依次尝试

Args:
    element_info: 元素信息，包含 locations 列表
        {
            'type': 主定位器类型,
            'value': 主定位器值,
            'locations': [
                {'type': 'id', 'value': 'username', 'priority': 1},
                {'type': 'ocr', 'value': '用户名', 'priority': 2}
            ]
        }

Returns:
    边界框坐标 (x1, y1, x2, y2)，所有定位器都失败返回 None

## _is_vision_locator

判断是否是视觉定位器类型

## _ensure_driver

确保驱动可用，如果已关闭则通过工厂重新创建

## _kw_close

关闭浏览器

## _kw_type

输入文本

## _extract_bracket_value

提取中文方括号【】中的参数值

## _execute_element_action

检查数据表值是否为 UI 动作关键字，是则执行对应操作。

Returns:
    (action_name, element_name, result) 或 None（表示不是动作，应当作文本输入）

## _batch_type

批量输入：遍历模型元素，匹配数据表字段

数据引用格式: type ModelName DataID
- 数据表名 = 模型名（强制一致）
- data_ref 直接就是 DataID

数据表单元格的值决定对该元素执行什么操作：
- 普通文本 → 输入到元素
- click / double_click / right_click / hover → 执行对应 UI 动作
- select【值】 → 下拉选择
- key_press【按键】 → 按键（支持组合键如 Control+C）
- drag【目标】 → 拖拽到目标元素
- scroll / scroll【x,y】 → 页面滚动

## _kw_send

发送接口请求 — 与 type 对称的接口测试关键字

公式: send ApiModel DataID
从模型获取接口定义（请求方式/URL），从数据表取值发送 HTTP 请求，
响应自动保存为步骤返回值（含 status 和响应体字段）。

## _batch_send

批量发送接口请求：从模型和数据表组装 HTTP 请求

数据引用格式: send ModelName DataID
- 数据表名 = 模型名（强制一致）
- data_ref 直接就是 DataID

接口模型元素命名约定：
- _method: HTTP 请求方式（GET/POST/PUT/DELETE），模型中定义默认值
- _url: 请求 URL（绝对路径或相对路径）
- _header_*: 请求头（如 _header_Authorization）
- 其他元素: 请求体字段（POST/PUT → JSON body；GET/DELETE → 查询参数）

## _kw_check

check → verify 的内部别名，保留向后兼容

## _kw_wait

等待

## _kw_navigate

导航到URL，如果当前没有浏览器则自动创建新实例

## _kw_launch

启动应用或打开页面

Web 模型: 等同于 navigate，打开 URL
Desktop 模型: 启动桌面应用

## _execute_navigate

执行 Web 导航

## _execute_desktop_launch

执行 Desktop 应用启动

## _kw_screenshot

截图

## _kw_verify_image

AI 截图验证 - 使用视觉大模型验证截图内容

公式: verify_image | screenshot_path | expected_description

Args:
    params: 包含 screenshot_path 和 expected 描述

Returns:
    验证通过返回 True，失败返回 False

## _kw_assert

断言（保留兼容）

## _kw_verify

验证 - 与 type 对称的批量验证关键字

公式: verify ModelName DataID
自动在 ModelName_verify 数据表中查找 DataID 行，
遍历模型元素，从界面/接口读取实际值并与期望值比较。

## _batch_verify

批量验证：遍历模型元素，读取界面/接口实际值，与期望值比较

数据引用格式: verify ModelName DataID
- 数据表名 = ModelName_verify（自动拼接）
- data_ref 直接就是 DataID

## _kw_get

获取元素文本（兼容老 SKI 的 get 关键字）

## _kw_clear

清空输入框

## _kw_get_text

获取文本

## _kw_upload_file

上传文件

## _kw_set

设置变量

## _kw_run

在沙箱中执行 Python 代码

用例格式: run | 工程名 | 代码文件路径
目录结构:
    test_project/
    ├── case/          ← 用例文件
    └── fun/           ← 代码工程根目录
        └── <工程名>/  ← model 列指定
            └── xxx.py ← data 列指定

脚本的 stdout 输出自动保存为步骤返回值（尝试 JSON 解析）。

## _kw_db

数据库操作

用例格式: DB | 连接变量名 | SQL数据引用或直接SQL

执行流程:
1. model 字段 = GlobalValue 中的数据库连接配置组名 (如 cassdb)
2. data 字段 = 数据表引用 (如 QuerySQL.Q001) 或直接 SQL
3. 从 GlobalValue 读取连接配置: cassdb.type, cassdb.host, cassdb.port 等
4. 如果 data 是数据表引用，从数据表中读取 sql/operation/var_name
5. 建立连接 → 执行 SQL → store_return 保存结果

## _resolve_db_sql

解析 DB 的 data 字段，返回 (sql, operation, var_name)

如果 data_ref 匹配 TableName.DataID 格式且数据表存在，从数据表读取:
    - sql 列: 实际 SQL
    - operation 列: query/execute (默认 query)
    - var_name 列: 可选，结果存入变量
否则视为直接 SQL 语句。

附带检查: 数据表对应的 .md 说明文件是否存在，不存在则自动创建空模板。

## _ensure_sql_doc

检查 SQL 数据表的 .md 说明文件是否存在，不存在则创建空模板

## _resolve_db_file_path

将 SQLite 的 database 相对路径解析为绝对路径（相对测试模块目录）。

## _get_db_connection

根据 GlobalValue 中的连接变量名获取/创建数据库连接

从 global_vars（通过 SKIExecutor 传入的 keyword_engine 上下文）读取:
    conn_var.type     → mysql / postgresql / sqlite
    conn_var.host     → 主机
    conn_var.port     → 端口
    conn_var.database → 数据库名
    conn_var.username → 用户名
    conn_var.password → 密码

## _create_connection

根据数据库类型创建连接

## _execute_db_sql

执行 SQL 并返回结果

