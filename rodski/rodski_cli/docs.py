"""docs 子命令 - 启动文档服务器"""
import subprocess
import sys
import shutil
from pathlib import Path

# VitePress 站点目录（相对于本文件）
_SITE_DIR = Path(__file__).parent.parent / "rodski_docs" / "site"
# 文档内容目录
_DOCS_DIR = Path(__file__).parent.parent / "docs"


def setup_parser(subparsers):
    parser = subparsers.add_parser("docs", help="文档站点管理")
    sub = parser.add_subparsers(dest="docs_action")

    dev_parser = sub.add_parser("dev", help="启动文档开发服务器")
    dev_parser.add_argument("--port", type=int, default=5173, help="端口号 (默认: 5173)")
    dev_parser.add_argument("--host", default="localhost", help="绑定地址 (默认: localhost)")

    build_parser = sub.add_parser("build", help="构建静态文档站点")
    build_parser.add_argument("--output", help="输出目录")

    sub.add_parser("preview", help="预览构建后的文档站点")


def _check_node():
    """检查 Node.js 是否可用且版本 >= 18"""
    if not shutil.which("node"):
        print("错误: 未找到 Node.js", file=sys.stderr)
        print("请安装 Node.js 18+: https://nodejs.org/", file=sys.stderr)
        return False

    result = subprocess.run(
        ["node", "--version"], capture_output=True, text=True
    )
    version = result.stdout.strip()
    major = int(version.lstrip("v").split(".")[0])
    if major < 18:
        print(f"错误: Node.js 版本过低 ({version})，需要 v18+", file=sys.stderr)
        return False
    return True


def _ensure_deps():
    """首次运行自动安装 npm 依赖"""
    node_modules = _SITE_DIR / "node_modules"
    if node_modules.exists():
        return True

    print("首次运行，正在安装 VitePress 依赖...")
    try:
        subprocess.run(
            ["npm", "install"],
            cwd=str(_SITE_DIR),
            check=True,
        )
        print("依赖安装完成\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("错误: 未找到 npm，请确认 Node.js 已正确安装", file=sys.stderr)
        return False


def handle(args):
    action = getattr(args, "docs_action", None)

    # 无子命令时默认启动开发服务器
    if action is None:
        action = "dev"

    # 检查目录
    if not _SITE_DIR.exists():
        print(f"错误: 文档站点目录不存在: {_SITE_DIR}", file=sys.stderr)
        return 1

    if not _DOCS_DIR.exists():
        print(f"错误: 文档内容目录不存在: {_DOCS_DIR}", file=sys.stderr)
        return 1

    # 检查 Node.js
    if not _check_node():
        return 1

    # 安装依赖
    if not _ensure_deps():
        return 1

    if action == "dev":
        port = getattr(args, "port", 5173)
        host = getattr(args, "host", "localhost")
        print(f"启动文档服务器: http://{host}:{port}")
        try:
            subprocess.run(
                ["npx", "vitepress", "dev", "--port", str(port), "--host", host],
                cwd=str(_SITE_DIR),
            )
        except KeyboardInterrupt:
            print("\n文档服务器已停止")
        return 0

    elif action == "build":
        cmd = ["npx", "vitepress", "build"]
        output = getattr(args, "output", None)
        if output:
            cmd.extend(["--outDir", str(Path(output).resolve())])
        try:
            subprocess.run(cmd, cwd=str(_SITE_DIR), check=True)
            print("文档站点构建完成")
        except subprocess.CalledProcessError as e:
            print(f"构建失败: {e}", file=sys.stderr)
            return 1
        return 0

    elif action == "preview":
        try:
            subprocess.run(
                ["npx", "vitepress", "preview"],
                cwd=str(_SITE_DIR),
            )
        except KeyboardInterrupt:
            print("\n预览已停止")
        return 0
