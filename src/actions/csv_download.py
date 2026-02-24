# -*- coding: utf-8 -*-
"""
kai_system - CSVダウンロード + Excel転記 アクション
旧 logic_robot.py の機能をプラグイン化
"""

import platform
import time as time_module
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.action_base import ActionBase, ActionResult
from core.action_manager import register_action
from infra.logger import logger


@register_action
class CSVDownloadAction(ActionBase):
    """CSVをダウンロードしてExcelに転記するアクション"""

    ACTION_TYPE = "csv_download"
    ACTION_LABEL = "CSVダウンロード + Excel転記"
    ACTION_DESCRIPTION = "WebサイトからCSVをダウンロードし、指定Excelファイルのシートに転記する"

    def validate_params(self, params: Dict[str, Any]) -> list:
        issues = []
        if not params.get("url") and not params.get("skip_download", False):
            issues.append("ダウンロードURL (url) が指定されていません")
        if not params.get("excel_path"):
            issues.append("Excelファイルパス (excel_path) が指定されていません")
        if not params.get("target_sheet") and not params.get("skip_download", False):
            issues.append("転記先シート名 (target_sheet) が指定されていません")
        return issues

    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """CSVダウンロード + Excel転記を実行"""
        excel_path = params.get("excel_path", "")
        target_sheet = params.get("target_sheet", "")
        url = params.get("url", "")
        action_after = params.get("action_after", "save").upper()
        skip_download = params.get("skip_download", False)
        close_after = params.get("close_after", False)
        macro_name = params.get("macro_name", "")

        file_name = Path(excel_path).name if excel_path else "(unknown)"
        system = platform.system()

        # Windows 専用チェック
        if system != "Windows":
            return ActionResult(
                success=False,
                message=f"CSVダウンロード+Excel転記はWindows専用です (現在: {system})",
                error="Unsupported platform",
            )

        self._notify_progress(f"開始: {file_name}", 0)

        try:
            # Windows COM 操作
            import win32com.client

            # Excel起動
            self._notify_progress(f"Excel起動中: {file_name}", 10)
            try:
                excel_app = win32com.client.GetActiveObject("Excel.Application")
            except Exception:
                excel_app = win32com.client.Dispatch("Excel.Application")

            excel_app.Visible = True
            excel_app.DisplayAlerts = False
            excel_app.AskToUpdateLinks = False

            # ファイルを開く
            self._notify_progress(f"ファイルを開いています: {file_name}", 20)
            if not Path(excel_path).exists():
                return ActionResult(
                    success=False,
                    message=f"ファイルが見つかりません: {excel_path}",
                    error="File not found",
                )

            workbook = excel_app.Workbooks.Open(
                excel_path,
                UpdateLinks=0,
                ReadOnly=False,
                IgnoreReadOnlyRecommended=True,
            )

            csv_path = None

            if not skip_download:
                # ダウンロード
                self._notify_progress(f"ダウンロード中: {file_name}", 40)
                webbrowser.open(url)

                # ダウンロード待機
                self._notify_progress(f"ダウンロード待機中: {file_name}", 50)
                csv_path = self._wait_for_csv_download()

                if csv_path is None:
                    workbook.Close(SaveChanges=False)
                    return ActionResult(
                        success=False,
                        message="CSVダウンロードに失敗しました",
                        error="Download timeout",
                    )

                # データ転記
                self._notify_progress(f"データ転記中: {target_sheet}", 70)
                csv_workbook = excel_app.Workbooks.Open(
                    str(csv_path), Format=2, Local=True
                )
                csv_sheet = csv_workbook.Sheets(1)
                csv_sheet.UsedRange.Copy()

                target = workbook.Sheets(target_sheet)
                target.Range("A1").PasteSpecial(Paste=-4163)  # xlPasteValues
                excel_app.CutCopyMode = False

                csv_workbook.Close(SaveChanges=False)

                # CSVを削除
                try:
                    csv_path.unlink()
                except Exception:
                    pass

            # マクロ実行
            if macro_name:
                self._notify_progress(f"マクロ実行中: {macro_name}", 80)
                try:
                    excel_app.Run(macro_name)
                except Exception as e:
                    logger.warning(f"マクロ実行に失敗: {macro_name} - {e}")

            # 保存処理
            if action_after == "SAVE":
                self._notify_progress(f"保存中: {file_name}", 90)
                workbook.Save()
            elif action_after == "PAUSE":
                # ユーザーに手動作業を促す
                import ctypes
                popup_msg = params.get("popup_message", "")
                if not popup_msg:
                    popup_msg = (
                        f"手動作業を行ってください。\n\n"
                        f"ファイル: {excel_path}\nシート: {target_sheet}\n\n"
                        f"作業完了後、OKを押してください。"
                    )
                ctypes.windll.user32.MessageBoxW(None, popup_msg, "kai_system - 手動作業", 0x40)
                try:
                    workbook.Save()
                except Exception:
                    pass

            # ファイルを閉じる
            if close_after:
                workbook.Close(SaveChanges=False)

            self._notify_progress(f"完了: {file_name}", 100)
            return ActionResult(
                success=True,
                message=f"完了: {file_name}",
            )

        except Exception as e:
            logger.error(f"CSVダウンロードエラー: {e}")
            return ActionResult(
                success=False,
                message=f"エラー: {file_name}",
                error=str(e),
            )

    def _wait_for_csv_download(self, timeout: int = 60, max_retries: int = 3) -> Optional[Path]:
        """ダウンロードフォルダを監視してCSVを取得"""
        import os, glob

        downloads = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
        if not downloads.exists():
            downloads = Path.home() / "Downloads"

        for attempt in range(max_retries):
            if attempt > 0:
                time_module.sleep(5)

            start = time_module.time()
            while time_module.time() - start < timeout:
                if self._stop_requested:
                    return None

                pattern = str(downloads / "*.csv")
                files = glob.glob(pattern)
                for f in files:
                    p = Path(f)
                    if p.suffix.lower() == ".csv":
                        # ロックチェック
                        try:
                            with open(p, "r+b"):
                                return p
                        except (IOError, PermissionError):
                            pass
                time_module.sleep(1)

        return None
