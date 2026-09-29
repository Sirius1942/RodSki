# qq_music - QQ 音乐 App 测试示例

## 概述

演示 RodSki 在真实第三方商业 App 上的自动化能力：在 Android 模拟器或真机上操作 QQ 音乐 App，验证移动端定位、交互、数据验证等核心能力。

## 环境要求

- **Appium** 服务（:4723）
- **Android 模拟器或真机**
- **QQ 音乐 App**（`com.tencent.qqmusic`）已安装
  - 需自行下载 APK 并安装到设备
  - 官网：https://y.qq.com/

## 用例说明

| 用例文件 | 说明 |
|---------|------|
| `case/*.xml` | QQ 音乐基础操作（搜索、播放、收藏等） |

具体用例数和覆盖范围以实际文件为准。

## 运行方式

```bash
# 1. 确保 Appium 已启动
appium

# 2. 确保设备已连接且 QQ 音乐已安装
adb devices
adb shell pm list packages | grep qqmusic

# 3. 运行用例
cd /path/to/rodski-demo/DEMO/qq_music
rodski run case/ --udid <your_device_udid>
```

## 验收标准

- 用例通过
- App 能正常启动并完成自动化操作
- 截图/录像正常生成

## 注意事项

- QQ 音乐版本更新可能导致定位器失效
- 首次运行可能需要手动授权（通知、存储等权限）
- 模拟器性能不足可能影响操作稳定性
