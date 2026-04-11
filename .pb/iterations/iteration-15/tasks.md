# Iteration 15 任务清单

## 任务汇总

| 任务 | 内容 | 预计 | 状态 | 负责人 |
|------|------|------|------|--------|
| T15-001 | 清理 data 目录 | 2h | 待开始 | - |
| T15-002 | 更新 README 文档 | 1h | 待开始 | - |
| T15-003 | 添加 Python 运行脚本 | 1h | 待开始 | - |

**总计**: 4h

---

## T15-001: 清理 data 目录

**预计**: 2h  
**文件**: `rodski-demo/DEMO/demo_full/data/`

### 步骤

1. 分析文件引用关系
   ```bash
   cd rodski-demo/DEMO/demo_full
   for file in data/*.xml; do
       name=$(basename $file .xml)
       echo "检查: $name"
       grep -r "$name" case/ model/ || echo "未使用: $file"
   done
   ```

2. 识别冗余文件
   - 重复命名的文件
   - 未被引用的文件
   - 测试遗留文件

3. 统一命名规范
   - 数据文件：模型名.xml
   - 验证文件：模型名_verify.xml

4. 创建 data/README.md
   - 说明文件组织结构
   - 说明命名规范
   - 列出所有数据文件及用途

### 验收
- [ ] data 目录文件数量 ≤ 30
- [ ] 命名规范统一
- [ ] data/README.md 已创建
- [ ] 现有测试用例不受影响

---

## T15-002: 更新 README 文档

**预计**: 1h  
**文件**: `rodski-demo/DEMO/demo_full/README.md`

### 步骤

1. 更新功能说明
   - 补充 expect_fail 功能
   - 补充 Auto Capture 功能
   - 补充结构化日志功能

2. 修正路径引用
   - 统一使用 `rodski-demo/` 前缀
   - 更新运行命令示例

3. 更新测试用例统计
   - 当前实际用例数量
   - 按类型分类统计

4. 删除过时说明
   - 删除"set关键字暂不支持"等过时信息

### 验收
- [ ] 功能说明完整准确
- [ ] 路径引用全部正确
- [ ] 测试用例统计准确
- [ ] 无过时信息

---

## T15-003: 添加 Python 运行脚本

**预计**: 1h  
**文件**: `rodski-demo/DEMO/demo_full/run_demo.py`

### 步骤

1. 创建 run_demo.py
   ```python
   #!/usr/bin/env python3
   """RodSki Demo 运行脚本"""
   import argparse
   import subprocess
   import sys
   from pathlib import Path
   
   def main():
       parser = argparse.ArgumentParser(description='RodSki Demo 运行脚本')
       parser.add_argument('--case', default='case/demo_case.xml', help='测试用例文件')
       parser.add_argument('--log-level', default='info', choices=['debug', 'info'], help='日志级别')
       parser.add_argument('--init-db', action='store_true', help='初始化数据库')
       args = parser.parse_args()
       
       demo_dir = Path(__file__).parent
       project_root = demo_dir.parent.parent.parent
       
       # 初始化数据库
       if args.init_db:
           print("🔧 初始化数据库...")
           subprocess.run([sys.executable, demo_dir / 'init_db.py'], check=True)
       
       # 运行测试
       print(f"🚀 运行测试用例: {args.case}")
       case_file = demo_dir / args.case
       cmd = [
           sys.executable,
           project_root / 'rodski' / 'ski_run.py',
           str(case_file),
           '--log-level', args.log_level
       ]
       subprocess.run(cmd, check=True)
       
       print("✅ 测试完成")
   
   if __name__ == '__main__':
       main()
   ```

2. 添加执行权限
   ```bash
   chmod +x run_demo.py
   ```

3. 测试脚本
   - Windows 测试
   - macOS 测试
   - Linux 测试

### 验收
- [ ] 脚本可以跨平台运行
- [ ] 支持所有参数
- [ ] 错误提示清晰
- [ ] 与 run_demo.sh 功能一致
