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

        mode = params.get("mode", "auto_table")

        if mode == "css_selector" and not params.get("selectors"):
            issues.append("CSSセレクタモードでは selectors が必要です")

        if mode in ("browser_session", "browser_csv"):
            # browser系モードでは output は任意（browser_csv はダウンロード先が自動決定）
            pass
        else:
            if not params.get("output"):
                issues.append("出力先 (output) が指定されていません")

        if mode == "browser_csv":
            if not params.get("download_button"):
                issues.append("ダウンロードボタンのセレクタ (download_button) が必要です")

        return issues

    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """スクレーピングを実行"""
        url = params.get("url", "")
        mode = params.get("mode", "auto_table")
        output = params.get("output", "")
        output_sheet = params.get("output_sheet", "Sheet1")

        self._notify_progress(f"スクレーピング開始: {url}", 0)

        try:
            if mode == "auto_table":
                return self._scrape_auto_table(url, output, output_sheet, params)
            elif mode == "css_selector":
                return self._scrape_css_selector(url, output, output_sheet, params)
            elif mode == "browser_session":
                return self._scrape_browser_session(url, output, output_sheet, params)
            elif mode == "browser_csv":
                return self._scrape_browser_csv(url, params)
            else:
                return ActionResult(
                    success=False,
                    message=f"未対応のモード: {mode}",
                    error=f"Unknown mode: {mode}",
                )

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
    # Mode: auto_table (Level 1 - 認証不要)
    # ----------------------------------------------------------------
    def _scrape_auto_table(
        self, url: str, output: str, sheet_name: str, params: Dict[str, Any]
    ) -> ActionResult:
        """テーブル自動検出"""
        import pandas as pd
        import requests

        self._notify_progress("ページを取得中...", 20)

        headers = params.get("headers", {})
        if not headers:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        self._notify_progress("テーブルを検出中...", 50)

        tables = pd.read_html(response.text, encoding=response.encoding)

        if not tables:
            return ActionResult(
                success=False,
                message="テーブルが見つかりませんでした",
                error="No tables found",
            )

        table_index = params.get("table_index", 0)
        if table_index >= len(tables):
            return ActionResult(
                success=False,
                message=f"テーブルインデックス {table_index} が範囲外 (検出: {len(tables)}個)",
                error="Table index out of range",
            )

        df = tables[table_index]
        self._notify_progress(f"出力中... ({len(df)} 行)", 80)
        self._write_output(df, output, sheet_name)

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"スクレイピング完了: {len(df)} 行取得 → {output}",
            data={"rows": len(df), "columns": len(df.columns), "output": output},
        )

    # ----------------------------------------------------------------
    # Mode: css_selector (Level 2 - 認証不要)
    # ----------------------------------------------------------------
    def _scrape_css_selector(
        self, url: str, output: str, sheet_name: str, params: Dict[str, Any]
    ) -> ActionResult:
        """CSSセレクタ指定"""
        import pandas as pd
        import requests
        from bs4 import BeautifulSoup

        self._notify_progress("ページを取得中...", 20)

        headers = params.get("headers", {})
        if not headers:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        self._notify_progress("データを抽出中...", 50)

        soup = BeautifulSoup(response.text, "html.parser")
        selectors = params.get("selectors", {})

        data = {}
        max_len = 0
        for field_name, css_selector in selectors.items():
            elements = soup.select(css_selector)
            values = [el.get_text(strip=True) for el in elements]
            data[field_name] = values
            max_len = max(max_len, len(values))

        if not data or max_len == 0:
            return ActionResult(
                success=False,
                message="指定されたセレクタでデータが見つかりませんでした",
                error="No data found with selectors",
            )

        for key in data:
            while len(data[key]) < max_len:
                data[key].append("")

        df = pd.DataFrame(data)
        self._notify_progress(f"出力中... ({len(df)} 行)", 80)
        self._write_output(df, output, sheet_name)

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"スクレイピング完了: {len(df)} 行取得 → {output}",
            data={"rows": len(df), "columns": len(df.columns), "output": output},
        )

    # ----------------------------------------------------------------
    # Mode: browser_session (Level 3 - 認証必要・テーブル取得)
    # ----------------------------------------------------------------
    def _scrape_browser_session(
        self, url: str, output: str, sheet_name: str, params: Dict[str, Any]
    ) -> ActionResult:
        """
        既存ブラウザセッションに接続してスクレーピング

        ユーザーが手動でログイン済みのブラウザに接続し、
        そのセッション（Cookie/認証状態）を利用してデータを取得する。

        前提: Chrome を --remote-debugging-port=9222 で起動済み
        """
        import pandas as pd
        from playwright.sync_api import sync_playwright

        cdp_url = params.get("cdp_url", "http://localhost:9222")
        wait_selector = params.get("wait_selector", "table")
        table_selector = params.get("table_selector", "table")
        table_index = params.get("table_index", 0)

        self._notify_progress("ブラウザに接続中...", 10)

        with sync_playwright() as pw:
            # 既存の Chrome に CDP で接続
            browser = pw.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]

            # 新しいタブでURLを開く
            page = context.new_page()

            self._notify_progress("ページを開いています...", 20)
            page.goto(url, wait_until="networkidle")

            # 要素の出現を待つ
            self._notify_progress("データの読み込みを待機中...", 40)
            page.wait_for_selector(wait_selector, timeout=30000)

            # フォーム操作（日付入力など）
            form_fills = params.get("form_fills", [])
            for fill in form_fills:
                selector = fill.get("selector", "")
                value = fill.get("value", "")
                action = fill.get("action", "fill")

                if action == "fill":
                    page.fill(selector, value)
                elif action == "select":
                    page.select_option(selector, value)
                elif action == "click":
                    page.click(selector)

                # 操作後の待機
                wait_after = fill.get("wait_after", 500)
                page.wait_for_timeout(wait_after)

            # 送信ボタンのクリック
            submit_button = params.get("submit_button", "")
            if submit_button:
                self._notify_progress("データを取得中...", 60)
                page.click(submit_button)
                page.wait_for_load_state("networkidle")
                page.wait_for_selector(wait_selector, timeout=30000)

            # テーブルデータを取得
            self._notify_progress("テーブルを抽出中...", 80)
            html = page.inner_html(table_selector)

            tables = pd.read_html(f"<table>{html}</table>")
            if not tables:
                page.close()
                return ActionResult(
                    success=False,
                    message="テーブルが見つかりませんでした",
                    error="No tables found",
                )

            idx = min(table_index, len(tables) - 1)
            df = tables[idx]

            page.close()

        # 出力
        if output:
            self._write_output(df, output, sheet_name)

        self._notify_progress("完了", 100)
        return ActionResult(
            success=True,
            message=f"ブラウザスクレイピング完了: {len(df)} 行取得",
            data={"rows": len(df), "columns": len(df.columns), "output": output},
        )

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

                if output:
                    # 指定された出力先に移動
                    import shutil
                    shutil.move(str(downloaded_path), output)
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
