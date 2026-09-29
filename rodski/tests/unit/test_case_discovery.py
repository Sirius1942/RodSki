"""Unit tests for case_discovery module (v11.5.0 nested case directories)"""
import pytest
from pathlib import Path
from rodski.core.case_discovery import (
    discover_case_files,
    resolve_module_dir,
    relative_case_file,
    RESERVED_CASE_SUBDIR_NAMES,
)
from rodski.core.exceptions import ReservedCaseSubdirNameError


class TestDiscoverCaseFiles:
    """测试 discover_case_files 递归发现用例文件"""

    def test_flat_directory(self, tmp_path):
        """扁平目录：兼容旧行为"""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        (case_dir / "a.xml").write_text("<cases/>")
        (case_dir / "b.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        names = [p.name for p in result]
        assert names == ["a.xml", "b.xml"]

    def test_nested_directories(self, tmp_path):
        """递归嵌套：按逐段排序"""
        case_dir = tmp_path / "case"
        (case_dir / "order").mkdir(parents=True)
        (case_dir / "order" / "refund").mkdir()
        (case_dir / "user").mkdir()

        (case_dir / "root.xml").write_text("<cases/>")
        (case_dir / "order" / "basic.xml").write_text("<cases/>")
        (case_dir / "order" / "refund" / "apply.xml").write_text("<cases/>")
        (case_dir / "user" / "login.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        rel_paths = [p.relative_to(case_dir).as_posix() for p in result]
        assert rel_paths == [
            "order/basic.xml",
            "order/refund/apply.xml",
            "root.xml",
            "user/login.xml",
        ]

    def test_segment_wise_sorting(self, tmp_path):
        """逐段排序：按路径段元组比较，短前缀在前"""
        case_dir = tmp_path / "case"
        (case_dir / "order-a").mkdir(parents=True)
        (case_dir / "order").mkdir()
        (case_dir / "order_b").mkdir()

        (case_dir / "order-a" / "x.xml").write_text("<cases/>")
        (case_dir / "order" / "y.xml").write_text("<cases/>")
        (case_dir / "order_b" / "z.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        rel_paths = [p.relative_to(case_dir).as_posix() for p in result]
        # 逐段排序：tuple(["order"]) < tuple(["order-a"]) < tuple(["order_b"])
        # （"order" 是 "order-a" 的前缀，短前缀在前）
        assert rel_paths == [
            "order/y.xml",
            "order-a/x.xml",
            "order_b/z.xml",
        ]

    def test_ignore_dot_prefix(self, tmp_path):
        """忽略 . 开头的目录和文件"""
        case_dir = tmp_path / "case"
        (case_dir / ".draft").mkdir(parents=True)
        (case_dir / ".draft" / "ignored.xml").write_text("<cases/>")
        (case_dir / ".hidden.xml").write_text("<cases/>")
        (case_dir / "visible.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        names = [p.name for p in result]
        assert names == ["visible.xml"]

    def test_ignore_non_xml_files(self, tmp_path):
        """忽略非 .xml 文件"""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        (case_dir / "README.md").write_text("docs")
        (case_dir / "test.txt").write_text("data")
        (case_dir / "case.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        names = [p.name for p in result]
        assert names == ["case.xml"]

    def test_reserved_subdir_name_raises(self, tmp_path):
        """子目录使用保留名时抛出 SKI206"""
        case_dir = tmp_path / "case"
        (case_dir / "order" / "model").mkdir(parents=True)
        (case_dir / "order" / "model" / "x.xml").write_text("<cases/>")

        with pytest.raises(ReservedCaseSubdirNameError) as exc_info:
            discover_case_files(case_dir)
        assert exc_info.value.error_code == "SKI206"
        assert "model" in exc_info.value.name
        assert "order/model" in exc_info.value.path

    def test_reserved_name_root_allowed(self, tmp_path):
        """根目录本身是 case，不触发保留名检查"""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        (case_dir / "test.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        assert len(result) == 1

    def test_symlink_directory_not_followed(self, tmp_path):
        """不跟随目录符号链接（防止循环引用）"""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        (real_dir / "real.xml").write_text("<cases/>")

        symlink_dir = case_dir / "link"
        symlink_dir.symlink_to(real_dir)
        (case_dir / "direct.xml").write_text("<cases/>")

        result = discover_case_files(case_dir)
        names = [p.name for p in result]
        # 只发现直接文件，不跟随符号链接目录
        assert names == ["direct.xml"]

    def test_symlink_file_allowed(self, tmp_path):
        """文件符号链接不被规范禁止（只是目录符号链接不跟随）"""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        real_file = tmp_path / "real.xml"
        real_file.write_text("<cases/>")

        symlink_file = case_dir / "link.xml"
        symlink_file.symlink_to(real_file)

        result = discover_case_files(case_dir)
        names = [p.name for p in result]
        assert "link.xml" in names

    def test_nonexistent_directory(self, tmp_path):
        """不存在的目录返回空列表"""
        result = discover_case_files(tmp_path / "nonexistent")
        assert result == []

    def test_file_instead_of_directory(self, tmp_path):
        """传入文件而非目录时返回空列表"""
        xml_file = tmp_path / "test.xml"
        xml_file.write_text("<cases/>")
        result = discover_case_files(xml_file)
        assert result == []


class TestResolveModuleDir:
    """测试 resolve_module_dir 向上查找 case 祖先"""

    def test_file_in_nested_case_dir(self, tmp_path):
        """case/ 下任意深度的文件 → 返回 case 的父目录"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "order" / "refund" / "apply.xml"
        case_file.parent.mkdir(parents=True)
        case_file.write_text("<cases/>")

        result = resolve_module_dir(case_file)
        assert result == module_dir

    def test_case_directory_itself(self, tmp_path):
        """传入 case 目录本身 → 返回其父目录"""
        module_dir = tmp_path / "module"
        case_dir = module_dir / "case"
        case_dir.mkdir(parents=True)

        result = resolve_module_dir(case_dir)
        assert result == module_dir

    def test_subdirectory_under_case(self, tmp_path):
        """case/ 下的子目录 → 返回 case 的父目录"""
        module_dir = tmp_path / "module"
        subdir = module_dir / "case" / "order"
        subdir.mkdir(parents=True)

        result = resolve_module_dir(subdir)
        assert result == module_dir

    def test_module_directory_no_case_ancestor(self, tmp_path):
        """没有 case 祖先时原样返回（视为已经是模块目录）"""
        module_dir = tmp_path / "module"
        module_dir.mkdir()

        result = resolve_module_dir(module_dir)
        assert result == module_dir

    def test_pure_path_no_filesystem_check(self):
        """纯路径名推导，不依赖文件系统存在性"""
        fake_path = Path("/nonexistent/module/case/order/x.xml")
        result = resolve_module_dir(fake_path)
        assert result == Path("/nonexistent/module")

    def test_multiple_case_ancestors_nearest_wins(self, tmp_path):
        """多个 case 祖先时返回最近的"""
        # 模拟嵌套项目结构（不推荐但需要正确处理）
        outer = tmp_path / "outer_module" / "case"
        inner = outer / "inner_module" / "case" / "order"
        inner.mkdir(parents=True)

        result = resolve_module_dir(inner)
        # 最近的 case 祖先是 inner_module/case，其父是 inner_module
        assert result.name == "inner_module"


class TestRelativeCaseFile:
    """测试 relative_case_file 计算相对路径"""

    def test_simple_relative_path(self, tmp_path):
        """简单相对路径计算"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "order" / "basic.xml"

        result = relative_case_file(module_dir, case_file)
        assert result == "order/basic.xml"

    def test_root_level_file(self, tmp_path):
        """case/ 根目录下的文件"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "smoke.xml"

        result = relative_case_file(module_dir, case_file)
        assert result == "smoke.xml"

    def test_deeply_nested_file(self, tmp_path):
        """深层嵌套文件"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "a" / "b" / "c" / "d.xml"

        result = relative_case_file(module_dir, case_file)
        assert result == "a/b/c/d.xml"

    def test_mixed_absolute_relative_paths(self, tmp_path):
        """混用绝对/相对路径时兜底为 resolve() 比较"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "test.xml"
        case_file.parent.mkdir(parents=True)
        case_file.write_text("<cases/>")

        # 传入相对路径（假设从其他 cwd 来的）
        result = relative_case_file(module_dir, case_file)
        assert result == "test.xml"

    def test_outside_case_root_raises(self, tmp_path):
        """文件不在 case/ 下时抛出 ValueError"""
        module_dir = tmp_path / "module"
        outside_file = tmp_path / "other" / "x.xml"

        with pytest.raises(ValueError):
            relative_case_file(module_dir, outside_file)


class TestReservedCaseSubdirNames:
    """测试保留名常量完整性"""

    def test_reserved_names_complete(self):
        """保留名集合包含所有模块目录名（CORE §6.4）"""
        expected = {
            "case", "model", "fun", "data", "plan", "result",
            "business", "perf", "knowledge",
        }
        assert RESERVED_CASE_SUBDIR_NAMES == expected

    def test_reserved_names_immutable(self):
        """保留名集合是 frozenset，不可变"""
        assert isinstance(RESERVED_CASE_SUBDIR_NAMES, frozenset)
