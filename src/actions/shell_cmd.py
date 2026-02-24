# -*- coding: utf-8 -*-
"""
kai_system - シェルコマンド実行 アクション
任意のコマンドを実行するプラグイン
"""

import platform
import subprocess
from typing import Any, Dict

from core.action_base import ActionBase, ActionResult
from core.action_manager import register_action
from infra.logger import logger


@register_action
class ShellCommandAction(ActionBase):
    """シェルコマンドを実行するアクション"""

    ACTION_TYPE = "shell_cmd"
    ACTION_LABEL = "シェルコマンド実行"
    ACTION_DESCRIPTION = "任意のシェルコマンドを実行する"

    def validate_params(self, params: Dict[str, Any]) -> list:
        issues = []
        if not params.get("command"):
            issues.append("コマンド (command) が指定されていません")
        return issues

    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """シェルコマンドを実行"""
        command = params.get("command", "")
        cwd = params.get("cwd", None)
        timeout = params.get("timeout", 300)  # デフォルト5分
        shell = params.get("shell", True)
        encoding = params.get("encoding", "utf-8")

        self._notify_progress(f"コマンド実行中: {command[:50]}...", 10)

        try:
            # プラットフォームに応じたシェル設定
            system = platform.system()
            if system == "Windows" and shell:
                # Windows の場合は cmd.exe を使う
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding=encoding,
                    cwd=cwd,
                    timeout=timeout,
                )
            else:
                result = subprocess.run(
                    command,
                    shell=shell,
                    capture_output=True,
                    text=True,
                    encoding=encoding,
                    cwd=cwd,
                    timeout=timeout,
                )

            self._notify_progress("完了", 100)

            if result.returncode == 0:
                logger.info(f"コマンド成功: {command}")
                stdout = result.stdout.strip() if result.stdout else ""
                return ActionResult(
                    success=True,
                    message=f"コマンド実行成功 (return code: 0)",
                    data={
                        "stdout": stdout[:1000],  # 最大1000文字
                        "stderr": result.stderr.strip()[:500] if result.stderr else "",
                        "return_code": 0,
                    },
                )
            else:
                logger.warning(f"コマンド失敗 (return code: {result.returncode}): {command}")
                return ActionResult(
                    success=False,
                    message=f"コマンド失敗 (return code: {result.returncode})",
                    error=result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}",
                    data={
                        "stdout": result.stdout.strip()[:1000] if result.stdout else "",
                        "stderr": result.stderr.strip()[:500] if result.stderr else "",
                        "return_code": result.returncode,
                    },
                )

        except subprocess.TimeoutExpired:
            logger.error(f"コマンドタイムアウト ({timeout}秒): {command}")
            return ActionResult(
                success=False,
                message=f"コマンドタイムアウト ({timeout}秒)",
                error="Timeout expired",
            )
        except Exception as e:
            logger.error(f"コマンド実行エラー: {e}")
            return ActionResult(
                success=False,
                message=f"コマンド実行エラー",
                error=str(e),
            )
