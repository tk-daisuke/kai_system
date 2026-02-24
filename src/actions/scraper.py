# -*- coding: utf-8 -*-
"""
kai_system - Webスクレーピング アクション
4段階のモードでWebからデータを取得する

Mode: auto_table   - URL + テーブル自動検出 (pandas.read_html) - 認証不要のページ向け
Mode: css_selector - URL + CSSセレクタ指定 (BeautifulSoup) - 認証不要のページ向け
Mode: browser_session - 既存ブラウザセッション引き継ぎ (Playwright) - 認証が必要なページ向け
Mode: browser_csv  - ブラウザ操作でCSVダウンロード (Playwright) - 認証+フォーム操作が必要

browser_session / browser_csv は、ユーザーが手動でログイン済みのブラウザに
Playwright で接続し、そのセッション（Cookie等）を引き継いでスクレーピングを行う。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.action_base import ActionBase, ActionResult
from core.action_manager import register_action
from infra.logger import logger


@register_action
class ScrapingAction(ActionBase):
    """Webスクレーピングアクション"""

    ACTION_TYPE = "scraper"
    ACTION_LABEL = "Webスクレーピング"
    ACTION_DESCRIPTION = "WebページからデータをスクレーピングしてExcel/CSVに出力する"

    def validate_params(self, params: Dict[str, Any]) -> list:
        issues = []
        if not params.get("url"):
            issues.append("URL (url) が指定されていません")

        if not params.get("download_button"):
            issues.append("ダウンロードボタンのセレクタ (download_button) が必要です")

        return issues

    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """スクレーピング（CSVダウンロード）を実行"""
        url = params.get("url", "")
        self._notify_progress(f"スクレーピング開始: {url}", 0)

        try:
            return self._scrape_browser_csv(url, params)
        except ImportError as e:
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
            return ActionResult(
                success=False,
                message=f"必要なライブラリがありません: {missing}",
                error=f"pip install {missing} を実行してください",
            )
        except Exception as e:
            logger.error(f"スクレーピングエラー: {e}")
            return ActionResult(
                success=False,
                message=f"スクレーピング失敗: {url}",
                error=str(e),
            )

    # モード廃止。ブラウザCSVダウンロードに統合

    # ----------------------------------------------------------------
    # Mode: browser_csv (Level 4 - 認証必要・CSVダウンロード操作)
    # ----------------------------------------------------------------
    def _scrape_browser_csv(
        self, url: str, params: Dict[str, Any]
    ) -> ActionResult:
        """
        既存ブラウザセッションでフォーム操作 → CSVダウンロード

        ユーザーの実際のワークフロー:
        1. ログイン済みのブラウザに接続
        2. 対象ページを開く
        3. 日時選択欄を埋める
        4. CSVダウンロードボタンを押す
        5. ダウンロードされたCSVを取得

        前提: Chrome を --remote-debugging-port=9222 で起動済み
        """
        import glob
        import time as time_module
        from playwright.sync_api import sync_playwright

        cdp_url = params.get("cdp_url", "http://localhost:9222")
        download_button = params.get("download_button", "")
        download_dir = params.get("download_dir", str(Path.home() / "Downloads"))
        output = params.get("output", "")
        download_timeout = params.get("download_timeout", 60)

        self._notify_progress("ブラウザに接続中...", 5)

        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            page = context.new_page()

            self._notify_progress("ページを開いています...", 15)
            page.goto(url, wait_until="networkidle")

            # フォーム操作（日付入力や選択など）
            form_fills = params.get("form_fills", [])
            for i, fill in enumerate(form_fills):
                selector = fill.get("selector", "")
                value = fill.get("value", "")
                action = fill.get("action", "fill")

                self._notify_progress(
                    f"フォーム入力中 ({i+1}/{len(form_fills)})...",
                    15 + (40 * (i + 1) / max(len(form_fills), 1))
                )

                if action == "fill":
                    page.fill(selector, value)
                elif action == "clear_and_fill":
                    page.click(selector, click_count=3)  # テキスト全選択
                    page.fill(selector, value)
                elif action == "select":
                    page.select_option(selector, value)
                elif action == "click":
                    page.click(selector)
                elif action == "type":
                    # 1文字ずつタイプ（日付ピッカー対応）
                    page.click(selector)
                    page.keyboard.type(value)

                wait_after = fill.get("wait_after", 500)
                page.wait_for_timeout(wait_after)

            # ダウンロード前のCSV一覧を記録
            existing_csvs = set(glob.glob(str(Path(download_dir) / "*.csv")))

            # CSVダウンロードボタンをクリック
            self._notify_progress("CSVダウンロードボタンをクリック...", 60)

            # Playwright のダウンロードイベントを監視
            try:
                with page.expect_download(timeout=download_timeout * 1000) as download_info:
                    page.click(download_button)

                download = download_info.value
                # ダウンロード完了を待つ
                downloaded_path = download.path()

                # 指定された出力先に保存または移動
                final_path = ""
                if output:
                    if str(output).lower().endswith(('.xlsx', '.xls')):
                        # Excel転記機能（プラグイン機能の統合）
                        final_path = self._transfer_to_excel(downloaded_path, output, params)
                    else:
                        import shutil
                        shutil.copy(str(downloaded_path), output)
                        final_path = output
                else:
                    # デフォルトのダウンロード先
                    suggested = download.suggested_filename
                    final_path = str(Path(download_dir) / suggested)
                    download.save_as(final_path)

                self._notify_progress("完了", 100)
                page.close()

                return ActionResult(
                    success=True,
                    message=f"CSVダウンロード完了: {final_path}",
                    data={"output": final_path},
                )

            except Exception as dl_err:
                logger.warning(f"Playwright download event失敗、フォールバック: {dl_err}")

                # フォールバック: ダウンロードフォルダを監視
                page.click(download_button)

                self._notify_progress("ダウンロード待機中...", 70)
                start = time_module.time()
                while time_module.time() - start < download_timeout:
                    if self._stop_requested:
                        page.close()
                        return ActionResult(
                            success=False, message="中断されました", error="Cancelled"
                        )

                    current_csvs = set(glob.glob(str(Path(download_dir) / "*.csv")))
                    new_csvs = current_csvs - existing_csvs
                    if new_csvs:
                        new_file = list(new_csvs)[0]
                        if output:
                            import shutil
                            shutil.move(new_file, output)
                            new_file = output

                        self._notify_progress("完了", 100)
                        page.close()

                        return ActionResult(
                            success=True,
                            message=f"CSVダウンロード完了: {new_file}",
                            data={"output": new_file},
                        )

                    time_module.sleep(1)

                page.close()
                return ActionResult(
                    success=False,
                    message="CSVダウンロードタイムアウト",
                    error=f"Timeout after {download_timeout}s",
                )

    def _transfer_to_excel(self, csv_path: Path, excel_path: str, params: Dict[str, Any]) -> str:
        """ダウンロードしたCSVをExcelに転記する (Windows COM使用)"""
        import platform
        if platform.system() != "Windows":
            logger.warning("Windows COM転記はWindows上でのみ動作します。CSVをそのまま保存します。")
            import shutil
            # Excelではないが、とりあえず output にコピー
            shutil.copy(str(csv_path), excel_path)
            return excel_path

        import win32com.client
        sheet_name = params.get("sheet_name", "Sheet1")
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = True
            wb = excel.Workbooks.Open(str(Path(excel_path).absolute()))
            
            # CSVを開いてコピー
            csv_wb = excel.Workbooks.Open(str(csv_path.absolute()), Format=2, Local=True)
            csv_wb.Sheets(1).UsedRange.Copy()
            
            # 転記
            try:
                target_ws = wb.Sheets(sheet_name)
            except:
                target_ws = wb.Sheets.Add()
                target_ws.Name = sheet_name
            
            target_ws.Range("A1").PasteSpecial(Paste=-4163) # xlPasteValues
            excel.CutCopyMode = False
            csv_wb.Close(False)
            
            wb.Save()
            return excel_path
        except Exception as e:
            logger.error(f"Excel転記失敗: {e}")
            raise

    # ----------------------------------------------------------------
    # ユーティリティ
    # ----------------------------------------------------------------
    def _write_output(self, df, output: str, sheet_name: str) -> None:
        """DataFrameを出力ファイルに書き込む"""
        output_path = Path(output)
        if output_path.suffix.lower() in (".xlsx", ".xls"):
            df.to_excel(output, sheet_name=sheet_name, index=False)
        else:
            df.to_csv(output, index=False, encoding="utf-8-sig")
