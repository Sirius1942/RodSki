# RodSki Web Dashboard 技术架构

## 1. 系统概述

RodSki Web Dashboard 是一款纯前端实现的 Web 应用，用于可视化展示 RodSki 自动化测试框架的测试数据。

### 1.1 设计目标
- 零后端依赖，纯浏览器端运行
- 轻量级，加载速度快
- 马里奥主题风格，提升用户体验
- 可作为 RodSki CLI 的一部分集成

### 1.2 技术选型

| 类别 | 技术 | 版本 | 说明 |
|-----|------|-----|------|
| 结构 | HTML5 | - | 语义化标签 |
| 样式 | Tailwind CSS | 3.x | 实用优先 CSS 框架 |
| 样式 | 自定义 CSS | - | 马里奥主题定制 |
| 图表 | ECharts | 5.x | 百度开源图表库 |
| 图标 | SVG 内联 | - | 马里奥元素图标 |
| 字体 | Google Fonts | - | Fredoka One, Nunito |
| 构建 | Vite | 5.x | 轻量级构建工具 |

---

## 2. 项目结构

```
rodski-dashboard/
├── src/
│   ├── index.html              # 首页入口
│   ├── cases.html              # 用例管理页
│   ├── models.html             # 模型管理页
│   ├── data.html               # 数据管理页
│   ├── results.html            # 测试结果页
│   ├── reports.html             # 报告页
│   │
│   ├── css/
│   │   ├── main.css            # 主样式文件
│   │   ├── components.css      # 组件样式
│   │   ├── mario-theme.css     # 马里奥主题
│   │   └── echarts-theme.css   # 图表主题
│   │
│   ├── js/
│   │   ├── app.js              # 主应用逻辑
│   │   ├── router.js           # 简单路由
│   │   ├── xml-parser.js       # XML 解析模块
│   │   ├── charts.js           # 图表配置
│   │   └── utils.js            # 工具函数
│   │
│   ├── components/
│   │   ├── navbar.html         # 导航栏组件
│   │   ├── sidebar.html        # 侧边栏组件
│   │   ├── stat-card.html      # 统计卡片组件
│   │   └── modal.html          # 弹窗组件
│   │
│   └── assets/
│       ├── icons/              # SVG 图标
│       └── images/             # 图片资源
│
├── mockups/                    # HTML 原型（静态）
│   ├── index.html
│   ├── cases.html
│   ├── models.html
│   ├── data.html
│   ├── results.html
│   ├── reports.html
│   └── styles.css
│
├── dist/                       # 构建输出
├── package.json
├── vite.config.js
├── tailwind.config.js
└── README.md
```

---

## 3. 核心模块设计

### 3.1 XML 解析模块 (xml-parser.js)

```javascript
// 主要功能
- parseTestCases(xml)      // 解析用例 XML
- parseModels(xml)         // 解析模型 XML
- parseTestData(xml)       // 解析测试数据 XML
- parseResults(xml)        // 解析测试结果 XML

// 数据结构
TestCase {
  id: string
  name: string
  module: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: 'active' | 'disabled'
  steps: TestStep[]
  expectedResult: string
  tags: string[]
}

Model {
  id: string
  name: string
  page: string
  elements: ModelElement[]
}

ModelElement {
  name: string
  type: 'button' | 'input' | 'link' | 'text' | ...
  locator: {
    id?: string
    xpath?: string
    css?: string
  }
}
```

### 3.2 路由模块 (router.js)

```javascript
// 路由配置
const routes = {
  '/': 'index.html',
  '/cases': 'cases.html',
  '/models': 'models.html',
  '/data': 'data.html',
  '/results': 'results.html',
  '/reports': 'reports.html'
}

// SPA 切换逻辑（可选）
- Hash 路由模式
- 页面片段加载
- 浏览器历史记录
```

### 3.3 图表模块 (charts.js)

```javascript
// ECharts 实例工厂
- createPieChart(container, data)
- createBarChart(container, data)
- createLineChart(container, data)

// 马里奥主题配置
const marioTheme = {
  color: ['#E52521', '#049CD8', '#38B044', '#F7D731'],
  // ... 其他主题配置
}
```

---

## 4. 数据流设计

### 4.1 数据加载流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  XML 文件   │ -> │ XML Parser  │ -> │  Data Store │
│ (rodcki/)   │    │  (浏览器)   │    │ (内存缓存)   │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   UI 渲染   │ <- │  View Layer │ <- │  状态更新    │
│  (HTML/CSS) │    │  (Vanilla JS)│   │  (事件触发)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 4.2 缓存策略

```javascript
// 内存缓存
const cache = {
  testCases: [...],
  models: [...],
  testData: [...],
  results: [...]
}

// 刷新机制
- 首次加载解析 XML
- 页面切换使用缓存
- 支持手动刷新按钮
- 启动时检测文件变化
```

---

## 5. 部署架构

### 5.1 独立部署模式

```
静态文件服务器 (Nginx/Node)
    │
    └── /dashboard/*
           ├── index.html
           ├── css/*
           ├── js/*
           └── assets/*
```

### 5.2 CLI 集成模式

```bash
# RodSki CLI 命令
$ rodski serve --port 3000

# 内部启动静态文件服务器
# 浏览器自动打开 http://localhost:3000
```

### 5.3 开发模式

```bash
# 启动 Vite 开发服务器
$ npm run dev

# 热重载支持
# Mock 数据可选
```

---

## 6. 性能优化

### 6.1 首屏加载优化
- CSS/JS 按需加载
- 图片资源压缩
- 字体子集加载

### 6.2 运行性能
- 虚拟列表（大数据量表格）
- 防抖搜索
- 图表懒加载

### 6.3 缓存优化
- XML 文件缓存
- 解析结果缓存
- 浏览器 IndexedDB

---

## 7. 浏览器兼容性

| 浏览器 | 最低版本 | 支持状态 |
|-------|---------|---------|
| Chrome | 90+ | ✅ 完全支持 |
| Firefox | 88+ | ✅ 完全支持 |
| Safari | 14+ | ✅ 完全支持 |
| Edge | 90+ | ✅ 完全支持 |

---

## 8. 扩展性设计

### 8.1 插件化架构
- 支持自定义页面
- 支持自定义图表类型
- 支持主题切换

### 8.2 数据源抽象
```javascript
// 可扩展的数据源
interface DataSource {
  loadTestCases(): Promise<TestCase[]>
  loadModels(): Promise<Model[]>
  loadTestData(): Promise<TestData[]>
  loadResults(): Promise<Result[]>
}

// 默认实现
class XMLDataSource implements DataSource { ... }

// 可扩展实现
class APIDataSource implements DataSource { ... }
class MockDataSource implements DataSource { ... }
```
