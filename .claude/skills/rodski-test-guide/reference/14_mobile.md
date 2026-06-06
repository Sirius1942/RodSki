<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 14. 移动端自动化（Mobile）

### 14.1 平台标识

移动端模型使用 `driver_type="android"` 或 `driver_type="ios"`：

```xml
<model name="QQMusicSearch" type="ui" driver_type="android">
  <element name="searchInput" type="android">
    <type>input</type>
    <location type="id" priority="1">com.tencent.qqmusic:id/searchItem</location>
    <location type="vision" priority="2">搜索输入框</location>
  </element>
</model>
```

### 14.2 启动 App（navigate + app:// URI）

移动端通过 `navigate` + `app://` URI 启动应用：

```xml
<!-- Android -->
<test_step action="navigate" model="" data="app://android/com.example.app/com.example.app.MainActivity"/>

<!-- iOS -->
<test_step action="navigate" model="" data="app://ios/com.example.app"/>
```

**URI 格式**：
- Android: `app://android/{包名}/{Activity名}`（Activity 可省略）
- iOS: `app://ios/{BundleId}`

也可通过 GlobalValue 引用：

```xml
<test_step action="navigate" model="" data="GlobalValue.Mobile.AppTarget"/>
```

### 14.3 Mobile GlobalValue 配置

```xml
<globalvalue>
  <group name="Mobile">
    <var name="Platform" value="android"/>
    <var name="AppiumServer" value="http://127.0.0.1:4723"/>
    <var name="DeviceName" value="设备序列号"/>
    <var name="AppPackage" value="com.example.app"/>
    <var name="AppActivity" value="com.example.app.MainActivity"/>
    <var name="AppTarget" value="app://android/com.example.app/com.example.app.MainActivity"/>
    <var name="NoReset" value="true"/>
    <var name="WaitTime" value="3"/>
  </group>
</globalvalue>
```

| Key | 说明 |
|-----|------|
| `Platform` | 平台类型：`android` / `ios` |
| `AppiumServer` | Appium 服务地址 |
| `DeviceName` | 设备名称或序列号 |
| `AppPackage` | Android 包名 |
| `AppActivity` | Android 启动 Activity |
| `BundleId` | iOS Bundle ID |
| `AppTarget` | app:// URI（供 navigate 使用） |
| `NoReset` | 是否保留应用状态（`true`/`false`） |
| `WaitTime` | 步骤间等待秒数 |

### 14.4 视觉定位降级策略（v7.0.1）

移动端 `vision` / `ocr` 定位器采用两级降级策略：

1. **Accessibility Tree 匹配**（快速路径）：解析 View Hierarchy，按文本/content-desc 精确匹配
2. **OmniParser 视觉模式**（降级路径）：截图后调用 OmniParser + LLM 语义匹配

```
vision 定位请求
  → 尝试 Accessibility Tree 文本匹配（毫秒级）
  → 匹配失败 → 截图 + OmniParser + LLM（秒级）
  → 均失败 → ElementNotFoundError
```

**推荐实践**：移动端模型优先使用 `id`/`text` 传统定位器（priority=1），`vision` 作为降级兜底（priority=2）。

### 14.5 完整示例

**globalvalue.xml**：
```xml
<globalvalue>
  <group name="Mobile">
    <var name="Platform" value="android"/>
    <var name="AppiumServer" value="http://127.0.0.1:4723"/>
    <var name="DeviceName" value="AKRSUT1618000209"/>
    <var name="AppPackage" value="com.tencent.qqmusic"/>
    <var name="AppActivity" value="com.tencent.qqmusic.activity.AppStarterActivity"/>
    <var name="AppTarget" value="app://android/com.tencent.qqmusic/com.tencent.qqmusic.activity.AppStarterActivity"/>
    <var name="NoReset" value="true"/>
  </group>
</globalvalue>
```

**model.xml**：
```xml
<models>
  <model name="QQMusicSearch" type="ui" driver_type="android">
    <element name="searchInput" type="android">
      <type>input</type>
      <location type="id" priority="1">com.tencent.qqmusic:id/searchItem</location>
      <location type="vision" priority="2">搜索输入框</location>
    </element>
    <element name="searchBtn" type="android">
      <type>button</type>
      <location type="text" priority="1">搜索</location>
      <location type="vision" priority="2">搜索按钮</location>
    </element>
  </model>
</models>
```

**case.xml**：
```xml
<cases tags="mobile,android">
  <case execute="是" id="QQ001" title="QQ音乐搜索" component_type="界面" priority="P0">
    <pre_process>
      <test_step action="navigate" model="" data="GlobalValue.Mobile.AppTarget"/>
      <test_step action="wait" model="" data="5"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="QQMusicSearch" data="S001"/>
      <test_step action="wait" model="" data="3"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
</cases>
```

### 14.6 约束

- ✅ 移动端 UI 操作统一使用 `type` 关键字（与 PC Web 一致）
- ✅ `close` 同时关闭移动端驱动并释放 Appium session
- ✅ 视觉定位器（vision/ocr/vision_bbox）在移动端完全支持
- ❌ 移动端不支持 `evaluate`（无 JavaScript 执行环境）
- ❌ 不新增 `swipe`、`long_press` 等独立关键字，通过数据表动作值或 `run` 脚本实现
