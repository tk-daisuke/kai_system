# -*- coding: utf-8 -*-
"""file_ops.py のユニットテスト"""
import tempfile
import zipfile
from pathlib import Path

import pytest

from actions.file_ops import FileOperationAction


class TestFileOpsValidation:

    def setup_method(self):
        self.action = FileOperationAction()

    def test_requires_operation(self):
        issues = self.action.validate_params({"source": "/a", "destination": "/b"})
        assert any("operation" in i for i in issues)

    def test_requires_source(self):
        issues = self.action.validate_params({"operation": "copy", "destination": "/b"})
        assert any("source" in i or "対象" in i for i in issues)

    def test_requires_destination(self):
        issues = self.action.validate_params({"operation": "copy", "source": "/a"})
        assert any("destination" in i or "出力先" in i for i in issues)

    def test_valid(self):
        issues = self.action.validate_params({
            "operation": "copy", "source": "/a", "destination": "/b",
        })
        assert issues == []


class TestCopyOperation:

    def setup_method(self):
        self.action = FileOperationAction()

    def test_copy_single_file(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            src.write_text("hello")
            dst = Path(td) / "dst.txt"

            result = self.action.execute({
                "operation": "copy",
                "source": str(src),
                "destination": str(dst),
            })

            assert result.success is True
            assert dst.read_text() == "hello"
            assert src.exists()  # 元ファイルは残る

    def test_copy_with_pattern(self):
        with tempfile.TemporaryDirectory() as td:
            src_dir = Path(td) / "src"
            src_dir.mkdir()
            (src_dir / "a.csv").write_text("a")
            (src_dir / "b.csv").write_text("b")
            (src_dir / "c.txt").write_text("c")

            dst_dir = Path(td) / "dst"

            result = self.action.execute({
                "operation": "copy",
                "source": str(src_dir),
                "destination": str(dst_dir),
                "pattern": "*.csv",
            })

            assert result.success is True
            assert result.data["count"] == 2

    def test_copy_no_files_found(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.action.execute({
                "operation": "copy",
                "source": str(Path(td) / "nonexistent"),
                "destination": str(Path(td) / "dst"),
                "pattern": "*.xyz",
            })
            assert result.success is False


class TestMoveOperation:

    def setup_method(self):
        self.action = FileOperationAction()

    def test_move_single_file(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            src.write_text("data")
            dst = Path(td) / "moved.txt"

            result = self.action.execute({
                "operation": "move",
                "source": str(src),
                "destination": str(dst),
            })

            assert result.success is True
            assert dst.read_text() == "data"
            assert not src.exists()  # 元ファイルは消える


class TestArchiveOperation:

    def setup_method(self):
        self.action = FileOperationAction()

    def test_archive_files(self):
        with tempfile.TemporaryDirectory() as td:
            src_dir = Path(td) / "src"
            src_dir.mkdir()
            (src_dir / "a.txt").write_text("aaa")
            (src_dir / "b.txt").write_text("bbb")

            zip_path = Path(td) / "archive.zip"

            result = self.action.execute({
                "operation": "archive",
                "source": str(src_dir),
                "destination": str(zip_path),
            })

            assert result.success is True
            assert zip_path.exists()

            with zipfile.ZipFile(str(zip_path)) as zf:
                names = zf.namelist()
                assert len(names) == 2

    def test_archive_auto_suffix(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "file.txt"
            src.write_text("x")

            result = self.action.execute({
                "operation": "archive",
                "source": str(src),
                "destination": str(Path(td) / "out"),
            })

            assert result.success is True
            assert (Path(td) / "out.zip").exists()
