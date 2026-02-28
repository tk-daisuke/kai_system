# -*- coding: utf-8 -*-
"""
kai_system - ファイル操作 アクション
ファイルのコピー・移動・アーカイブ(zip)を行うプラグイン
"""

import glob
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from core.action_base import ActionBase, ActionResult
from core.action_manager import register_action
from infra.logger import logger


@register_action
class FileOperationAction(ActionBase):
    """ファイル操作アクション"""

    ACTION_TYPE = "file_ops"
    ACTION_LABEL = "ファイル操作"
    ACTION_DESCRIPTION = "ファイルのコピー・移動・ZIP圧縮を行う"

    def validate_params(self, params: Dict[str, Any]) -> list:
        issues = []
        operation = params.get("operation", "")
        if operation not in ("copy", "move", "archive"):
            issues.append("操作 (operation) は copy / move / archive のいずれかを指定してください")

        if not params.get("source"):
            issues.append("対象パス (source) が指定されていません")

        if not params.get("destination"):
            issues.append("出力先 (destination) が指定されていません")

        return issues

    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """ファイル操作を実行"""
        operation = params.get("operation", "copy")
        source = params.get("source", "")
        destination = params.get("destination", "")
        pattern = params.get("pattern", "")

        self._notify_progress(f"ファイル操作開始: {operation}", 0)

        try:
            # glob パターンでファイル一覧を取得
            files = self._resolve_files(source, pattern)
            if not files:
                return ActionResult(
                    success=False,
                    message="対象ファイルが見つかりませんでした",
                    error=f"source={source}, pattern={pattern}",
                )

            if operation == "copy":
                return self._do_copy(files, destination)
            elif operation == "move":
                return self._do_move(files, destination)
            elif operation == "archive":
                return self._do_archive(files, destination)
            else:
                return ActionResult(
                    success=False,
                    message=f"不明な操作: {operation}",
                    error="operation は copy / move / archive のいずれかを指定してください",
                )

        except Exception as e:
            logger.error(f"ファイル操作エラー: {e}")
            return ActionResult(
                success=False,
                message=f"ファイル操作失敗: {operation}",
                error=str(e),
            )

    def _resolve_files(self, source: str, pattern: str) -> List[Path]:
        """source と pattern からファイル一覧を解決"""
        source_path = Path(source)

        if pattern:
            # source をディレクトリとして、pattern で glob
            if source_path.is_dir():
                return sorted(source_path.glob(pattern))
            else:
                # source 自体が glob パターンを含む可能性
                return sorted(Path(p) for p in glob.glob(str(source_path / pattern)))
        else:
            if source_path.is_file():
                return [source_path]
            elif source_path.is_dir():
                return sorted(source_path.iterdir())
            else:
                # glob パターンとして解釈
                return sorted(Path(p) for p in glob.glob(source))

    def _do_copy(self, files: List[Path], destination: str) -> ActionResult:
        """ファイルをコピー"""
        dest = Path(destination)
        copied = []

        for i, f in enumerate(files):
            if self._stop_requested:
                return ActionResult(success=False, message="中断されました", error="Cancelled")

            self._notify_progress(
                f"コピー中 ({i+1}/{len(files)}): {f.name}",
                (i + 1) / len(files) * 100
            )

            if f.is_file():
                if dest.is_dir() or (len(files) > 1 and not dest.suffix):
                    dest.mkdir(parents=True, exist_ok=True)
                    target = dest / f.name
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    target = dest
                shutil.copy2(str(f), str(target))
                copied.append(str(target))
            elif f.is_dir():
                target = dest / f.name if dest.exists() else dest
                shutil.copytree(str(f), str(target), dirs_exist_ok=True)
                copied.append(str(target))

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"コピー完了: {len(copied)}件 -> {destination}",
            data={"files": copied, "count": len(copied)},
        )

    def _do_move(self, files: List[Path], destination: str) -> ActionResult:
        """ファイルを移動"""
        dest = Path(destination)
        moved = []

        for i, f in enumerate(files):
            if self._stop_requested:
                return ActionResult(success=False, message="中断されました", error="Cancelled")

            self._notify_progress(
                f"移動中 ({i+1}/{len(files)}): {f.name}",
                (i + 1) / len(files) * 100
            )

            if len(files) > 1 or dest.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                target = dest / f.name
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                target = dest

            shutil.move(str(f), str(target))
            moved.append(str(target))

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"移動完了: {len(moved)}件 -> {destination}",
            data={"files": moved, "count": len(moved)},
        )

    def _do_archive(self, files: List[Path], destination: str) -> ActionResult:
        """ファイルをZIP圧縮"""
        dest = Path(destination)
        if not dest.suffix:
            dest = dest.with_suffix(".zip")
        dest.parent.mkdir(parents=True, exist_ok=True)

        archived = []
        with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
            for i, f in enumerate(files):
                if self._stop_requested:
                    return ActionResult(success=False, message="中断されました", error="Cancelled")

                self._notify_progress(
                    f"圧縮中 ({i+1}/{len(files)}): {f.name}",
                    (i + 1) / len(files) * 100
                )

                if f.is_file():
                    zf.write(str(f), f.name)
                    archived.append(f.name)
                elif f.is_dir():
                    for child in f.rglob("*"):
                        if child.is_file():
                            arcname = str(child.relative_to(f.parent))
                            zf.write(str(child), arcname)
                            archived.append(arcname)

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"アーカイブ完了: {len(archived)}件 -> {dest}",
            data={"archive": str(dest), "files": archived, "count": len(archived)},
        )
