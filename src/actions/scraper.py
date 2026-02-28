# -*- coding: utf-8 -*-
"""
kai_system - Webスクレーピング アクション
3つのモードでWebからデータを取得する

Mode: auto_table   - URL + テーブル自動検出 (pandas.read_html) - 認証不要のページ向け
Mode: css_selector - URL + CSSセレクタ指定 (BeautifulSoup) - 認証不要のページ向け
Mode: browser_csv  - ブラウザ操作でCSVダウンロード (Playwright) - 認証+フォーム操作が必要
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
        mode = params.get("mode", "browser_csv")

        if not params.get("url"):
            issues.append("URL (url) が指定されていません")

        if mode == "browser_csv":
            if not params.get("download_button"):
                issues.append("ダウンロードボタンのセレクタ (download_button) が必要です")
        elif mode == "auto_table":
            if not params.get("output"):
                issues.append("出力先 (output) が指定されていません")
        elif mode == "css_selector":
            if not params.get("selectors"):
                issues.append("CSSセレクタ定義 (selectors) が必要です")
            if not params.get("output"):
                issues.append("出力先 (output) が指定されていません")

        return issues

    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """モードに応じてスクレーピングを実行"""
        url = params.get("url", "")
        mode = params.get("mode", "browser_csv")
        self._notify_progress(f"スクレーピング開始 [{mode}]: {url}", 0)

        try:
            if mode == "auto_table":
                return self._scrape_auto_table(url, params)
            elif mode == "css_selector":
                return self._scrape_css_selector(url, params)
            else:
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

    # ----------------------------------------------------------------
    # Mode: auto_table (テーブル自動検出)
    # ----------------------------------------------------------------
    def _scrape_auto_table(
        self, url: str, params: Dict[str, Any]
    ) -> ActionResult:
        """pandas.read_html でHTMLテーブルを自動検出して取得"""
        import pandas as pd
        import requests

        table_index = params.get("table_index", 0)
        output = params.get("output", "")
        output_sheet = params.get("output_sheet", "Sheet1")

        self._notify_progress("HTMLを取得中...", 20)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        self._notify_progress("テーブルを解析中...", 50)
        tables = pd.read_html(resp.text)

        if not tables:
            return ActionResult(
                success=False,
                message="テーブルが見つかりませんでした",
                error=f"URL: {url} にHTMLテーブルが存在しません",
            )

        if table_index >= len(tables):
            return ActionResult(
                success=False,
                message=f"テーブルインデックス {table_index} が範囲外です（{len(tables)}個検出）",
                error=f"table_index は 0〜{len(tables) - 1} の範囲で指定してください",
            )

        df = tables[table_index]

        self._notify_progress("出力中...", 80)
        self._write_output(df, output, output_sheet)

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"テーブル取得完了: {len(df)}行 -> {output}",
            data={"output": output, "rows": len(df), "columns": len(df.columns)},
        )

    # ----------------------------------------------------------------
    # Mode: css_selector (CSSセレクタ指定)
    # ----------------------------------------------------------------
    def _scrape_css_selector(
        self, url: str, params: Dict[str, Any]
    ) -> ActionResult:
        """BeautifulSoup でCSSセレクタ指定の要素を抽出"""
        import pandas as pd
        import requests
        from bs4 import BeautifulSoup

        selectors = params.get("selectors", {})
        output = params.get("output", "")
        output_sheet = params.get("output_sheet", "Sheet1")

        self._notify_progress("HTMLを取得中...", 20)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        self._notify_progress("要素を抽出中...", 50)
        soup = BeautifulSoup(resp.text, "html.parser")

        data: Dict[str, List[str]] = {}
        max_len = 0
        for col_name, selector in selectors.items():
            elements = soup.select(selector)
            texts = [el.get_text(strip=True) for el in elements]
            data[col_name] = texts
            max_len = max(max_len, len(texts))

        if max_len == 0:
            return ActionResult(
                success=False,
                message="指定されたセレクタに一致する要素が見つかりませんでした",
                error=f"selectors: {selectors}",
            )

        # 長さを揃える
        for col_name in data:
            while len(data[col_name]) < max_len:
                data[col_name].append("")

        df = pd.DataFrame(data)

        self._notify_progress("出力中...", 80)
        self._write_output(df, output, output_sheet)

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"CSS抽出完了: {len(df)}行 -> {output}",
            data={"output": output, "rows": len(df), "columns": len(df.columns)},
        )

    # ----------------------------------------------------------------
    # Mode: browser_csv (認証必要・CSVダウンロード操作)
    # ----------------------------------------------------------------
    def _scrape_browser_csv(
        self, url: str, params: Dict[str, Any]
    ) -> ActionResult:
        """
        既存ブラウザセッションでフォーム操作 -> CSVダウンロード

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
                    page.click(selector, click_count=3)
                    page.fill(selector, value)
                elif action == "select":
                    page.select_option(selector, value)
                elif action == "click":
                    page.click(selector)
                elif action == "type":
                    page.click(selector)
                    page.keyboard.type(value)

                wait_after = fill.get("wait_after", 500)
                page.wait_for_timeout(wait_after)

            # ダウンロード前のCSV一覧を記録
            existing_csvs = set(glob.glob(str(Path(download_dir) / "*.csv")))

            # CSVダウンロードボタンをクリック
            self._notify_progress("CSVダウンロードボタンをクリック...", 60)

            try:
                with page.expect_download(timeout=download_timeout * 1000) as download_info:
                    page.click(download_button)

                download = download_info.value
                downloaded_path = download.path()

                final_path = ""
                if output:
                    if str(output).lower().endswith(('.xlsx', '.xls')):
                        final_path = self._transfer_to_excel(downloaded_path, output, params)
                    else:
                        import shutil
                        shutil.copy(str(downloaded_path), output)
                        final_path = output
                else:
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
            shutil.copy(str(csv_path), excel_path)
            return excel_path

        import win32com.client
        sheet_name = params.get("sheet_name", "Sheet1")
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = True
            wb = excel.Workbooks.Open(str(Path(excel_path).absolute()))

            csv_wb = excel.Workbooks.Open(str(csv_path.absolute()), Format=2, Local=True)
            csv_wb.Sheets(1).UsedRange.Copy()

            try:
                target_ws = wb.Sheets(sheet_name)
            except Exception:
                target_ws = wb.Sheets.Add()
                target_ws.Name = sheet_name

            target_ws.Range("A1").PasteSpecial(Paste=-4163)
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() in (".xlsx", ".xls"):
            df.to_excel(output, sheet_name=sheet_name, index=False)
        else:
            df.to_csv(output, index=False, encoding="utf-8-sig")
