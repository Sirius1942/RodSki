# Iteration 06: 动态执行能力

## 功能概述

实现了三个核心动态执行能力：
1. 运行时步骤插入（CLI 参数）
2. 条件执行（if 语句）
3. 循环执行（loop 语句）

## 1. 运行时步骤插入

### CLI 参数

```bash
ski run case.xml --insert-step "action,model,data"
```

### 示例

```bash
# 插入单个步骤
ski run case.xml --insert-step "log,,开始测试"

# 插入多个步骤
ski run case.xml --insert-step "navigate,,https://example.com" --insert-step "wait,,2"
```

## 2. 条件执行

### XML 格式

```xml
<if condition="表达式">
  <test_step action="..." model="..." data="..."/>
</if>
```

### 支持的条件运算符

- `==` 等于
- `!=` 不等于
- `>` 大于
- `<` 小于
- `>=` 大于等于
- `<=` 小于等于

### 示例

```xml
<if condition="$status==success">
  <test_step action="log" data="测试通过"/>
</if>

<if condition="$count>5">
  <test_step action="log" data="数量超过阈值"/>
</if>
```

## 3. 循环执行

### XML 格式

```xml
<loop range="范围" var="变量名">
  <test_step action="..." model="..." data="..."/>
</loop>
```

### 支持的范围格式

- `1-5` 数字范围（1,2,3,4,5）
- `a,b,c` 逗号分隔列表
- `$varname` 变量引用

### 示例

```xml
<!-- 数字范围 -->
<loop range="1-3" var="i">
  <test_step action="log" data="第 $i 次"/>
</loop>

<!-- 列表 -->
<loop range="chrome,firefox,safari" var="browser">
  <test_step action="log" data="测试浏览器: $browser"/>
</loop>
```

## 4. 混合使用

条件和循环可以嵌套使用：

```xml
<loop range="1-3" var="round">
  <test_step action="log" data="第 $round 轮"/>

  <if condition="$round==1">
    <test_step action="log" data="首轮特殊处理"/>
  </if>
</loop>
```

## 实现文件

- `core/dynamic_executor.py` - 动态执行引擎
- `core/case_parser.py` - 支持 if/loop 解析
- `core/ski_executor.py` - 集成动态执行
- `rodski_cli/run.py` - CLI 参数支持

## 向后兼容

- 现有 XML 格式完全兼容
- 不使用新特性的用例无需修改
- 新特性为可选功能
