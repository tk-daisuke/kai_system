# -*- coding: utf-8 -*-
"""
Co-worker Bot - ロボットロジックモジュール
Excel操作、ダウンロード処理、ファイル監視を行う
"""

import time as time_module
import webbrowser
from datetime import datetime, time
from pathlib import Path
from typing import Optional, List
import glob

import traceback
import win32com.client

from config_loader import TaskConfig
from utils import (
    logger, 
    get_downloads_folder, 
    is_file_locked, 
    safe_delete_file,
    show_info,
    show_warning,
    confirm_dialog
)
from holiday_checker import should_skip_task


class ExcelHandler:
    """Excel操作を行うクラス"""
    
    def __init__(self):
        self.excel_app = None
        self.workbook = None
    
    def start_excel(self, visible: bool = True) -> bool:
        """Excelアプリケーションを起動"""
        try:
            # 既存のExcelインスタンスを取得するか、新規作成
            try:
                self.excel_app = win32com.client.GetActiveObject("Excel.Application")
                logger.info("既存のExcelインスタンスを使用します")
            except:
                self.excel_app = win32com.client.Dispatch("Excel.Application")
                logger.info("新しいExcelインスタンスを起動しました")
            
            self.excel_app.Visible = visible
            self.excel_app.DisplayAlerts = False  # 警告ダイアログを抑制
            self.excel_app.AskToUpdateLinks = False  # リンク更新の確認を抑制
            return True
        except Exception as e:
            logger.error(f"Excel起動エラー: {e}")
            return False
    
    def open_workbook(self, file_path: str) -> bool:
        """ワークブックを開く"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"ファイルが見つかりません: {file_path}")
                return False
            
            # ファイルロック検出（最大3回リトライ）
            max_lock_retries = 3
            for attempt in range(max_lock_retries):
                if not is_file_locked(path):
                    break
                    
                logger.warning(f"ファイルがロックされています: {file_path} (試行 {attempt + 1}/{max_lock_retries})")
                
                if attempt < max_lock_retries - 1:
                    # ユーザーに確認
                    import ctypes
                    result = ctypes.windll.user32.MessageBoxW(
                        None,
                        f"ファイルが他のプロセスで開かれています:\n{path.name}\n\n"
                        "ファイルを閉じてから「再試行」を押してください。\n"
                        "スキップする場合は「キャンセル」を押してください。",
                        "ファイルロック検出",
                        0x05 | 0x30  # MB_RETRYCANCEL | MB_ICONWARNING
                    )
                    
                    if result == 2:  # Cancel
                        logger.warning("ユーザーによりスキップされました")
                        return False
                    # Retry = 4 → 続行
                else:
                    logger.error(f"ファイルロックが解除されませんでした: {file_path}")
                    show_warning("ファイルロック", f"ファイルを開けませんでした:\n{path.name}")
                    return False
            
            # UpdateLinks=0: リンクを更新しない
            # ReadOnly=False: 読み取り専用で開かない
            # IgnoreReadOnlyRecommended=True: 読み取り専用推奨ダイアログを無視
            self.workbook = self.excel_app.Workbooks.Open(
                file_path,
                UpdateLinks=0,
                ReadOnly=False,
                IgnoreReadOnlyRecommended=True
            )
            logger.info(f"ワークブックを開きました: {file_path}")
            return True
        except Exception as e:
            logger.error(f"ワークブックを開けませんでした: {file_path} - {e}")
            return False
    
    def paste_data_to_sheet(self, sheet_name: str, csv_path: Path) -> bool:
        """CSVデータをシートに貼り付け"""
        csv_workbook = None
        try:
            # CSVをExcelで開く（文字化け回避）
            csv_workbook = self.excel_app.Workbooks.Open(
                str(csv_path),
                Format=2,  # カンマ区切り
                Local=True
            )
            csv_sheet = csv_workbook.Sheets(1)
            
            # 使用範囲をコピー
            used_range = csv_sheet.UsedRange
            used_range.Copy()
            
            # 対象シートにペースト（値のみ）
            target_sheet = self.workbook.Sheets(sheet_name)
            # xlPasteValues = -4163
            target_sheet.Range("A1").PasteSpecial(Paste=-4163)
            
            # クリップボードをクリア
            self.excel_app.CutCopyMode = False
            
            logger.info(f"データを {sheet_name} シートに貼り付けました")
            return True
            
        except Exception as e:
            logger.error(f"データ貼り付けエラー: {e}")
            return False
        
        finally:
            # CSVワークブックを閉じる
            if csv_workbook:
                try:
                    csv_workbook.Close(SaveChanges=False)
                except:
                    pass
    
    def save_workbook(self) -> bool:
        """ワークブックを保存"""
        try:
            self.workbook.Save()
            logger.info("ワークブックを保存しました")
            return True
        except Exception as e:
            logger.error(f"保存エラー: {e}")
            return False
    
    def close_workbook(self, save: bool = False) -> None:
        """ワークブックを閉じる"""
        try:
            if self.workbook:
                self.workbook.Close(SaveChanges=save)
                self.workbook = None
                logger.info("ワークブックを閉じました")
        except Exception as e:
            logger.error(f"ワークブックを閉じる際にエラー: {e}")
    
    def quit_excel(self) -> None:
        """Excelアプリケーションを終了"""
        try:
            if self.excel_app:
                self.excel_app.Quit()
                self.excel_app = None
                logger.info("Excelアプリケーションを終了しました")
        except Exception as e:
            logger.error(f"Excel終了エラー: {e}")

    def run_macro(self, macro_name: str) -> bool:
        """指定したマクロを実行する"""
        try:
            # マクロ名は 'Book1!MacroName' のように指定される場合もあるが、
            # 単に 'MacroName' だけでも標準モジュールなら動くことが多い。
            logger.info(f"マクロを実行中: {macro_name}")
            self.excel_app.Run(macro_name)
            logger.info(f"マクロ実行完了: {macro_name}")
            return True
        except Exception as e:
            logger.error(f"マクロ実行エラー ({macro_name}): {e}")
            return False


class DownloadHandler:
    """ダウンロード処理を行うクラス"""
    
    def __init__(self, timeout: int = 60):
        self.downloads_folder = get_downloads_folder()
        self.timeout = timeout
        self.skip_csv_confirm = False  # セッション中の確認スキップフラグ
    
    def cleanup_existing_csv(self, search_key: str = "") -> bool:
        """
        ダウンロードフォルダ内の既存CSVファイルを削除する
        
        Args:
            search_key: (廃止予定) 互換性のため残すが使用しない
            
        Returns:
            削除実行（または削除対象なし）ならTrue
            ユーザーキャンセルならFalse
        """
        # 全てのCSVを対象にする
        pattern = str(self.downloads_folder / "*.csv")
        files = glob.glob(pattern)
        
        if not files:
            return True
        
        # セッション中スキップが有効なら確認なしで削除
        if self.skip_csv_confirm:
            logger.info(f"確認スキップ中: {len(files)} 個のCSVを削除します")
            for file_path in files:
                safe_delete_file(Path(file_path))
            return True
            
        # ファイルがある場合は確認（Yes/No/今後確認しない）
        msg = (
            f"ダウンロードフォルダに {len(files)} 個のCSVファイルがあります。\n"
            "誤処理を防ぐため、これらを全て削除してからダウンロードを開始します。\n\n"
            "【はい】削除して続行\n"
            "【いいえ】タスクを中断\n"
            "【キャンセル】今後このセッション中は確認せず削除"
        )
        
        # Yes=6, No=7, Cancel=2
        import ctypes
        result = ctypes.windll.user32.MessageBoxW(
            None, msg, "既存ファイルの削除確認",
            0x03 | 0x30  # MB_YESNOCANCEL | MB_ICONWARNING
        )
        
        if result == 7:  # No
            logger.warning("ユーザーによりCSV削除がキャンセルされました。タスクを中断します。")
            return False
        elif result == 2:  # Cancel = 今後確認しない
            self.skip_csv_confirm = True
            logger.info("今後のCSV削除確認をスキップします")
            
        for file_path in files:
            safe_delete_file(Path(file_path))
            
        return True
    
    def download_direct(self, url: str, search_key: str) -> Optional[Path]:
        """
        HTTPで直接ダウンロードする（ブラウザを使わない）
        
        Args:
            url: ダウンロードURL
            search_key: ファイル名に含めるキーワード
            
        Returns:
            ダウンロードしたファイルのパス
        """
        import urllib.request
        import urllib.error
        
        try:
            logger.info(f"HTTP直接ダウンロード中: {url}")
            
            # ファイル名を生成
            filename = f"{search_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = self.downloads_folder / filename
            
            # ダウンロード
            urllib.request.urlretrieve(url, filepath)
            
            if filepath.exists():
                logger.success(f"ダウンロード完了: {filepath}")
                return filepath
            else:
                logger.error("ダウンロードしたがファイルが見つかりません")
                return None
                
        except urllib.error.URLError as e:
            logger.error(f"URLエラー（ネットワークまたはサーバーの問題）: {e}")
            return None
        except Exception as e:
            logger.error(f"ダウンロードエラー: {e}")
            return None
    
    def trigger_download(self, url: str) -> bool:
        """ブラウザでURLを開いてダウンロードをトリガー"""
        try:
            logger.info(f"ダウンロードURLを開きます: {url}")
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"URL起動エラー: {e}")
            return False
    
    def wait_for_download(self, search_key: str, max_retries: int = 3, retry_delay: int = 5) -> Optional[Path]:
        """
        ダウンロードフォルダを監視し、CSVファイルの完了を待つ（リトライ機能付き）
        
        Args:
            search_key: ファイル名に含まれるキーワード（現在未使用）
            max_retries: 最大リトライ回数
            retry_delay: リトライ間隔（秒）
            
        Returns:
            ダウンロードされたファイルのパス、タイムアウト時はNone
        """
        for attempt in range(max_retries):
            if attempt > 0:
                logger.info(f"ダウンロードリトライ中... ({attempt + 1}/{max_retries})")
                time_module.sleep(retry_delay)
            
            logger.info(f"ダウンロード待機中... (タイムアウト: {self.timeout}秒)")
            
            start_time = time_module.time()
            
            while time_module.time() - start_time < self.timeout:
                # CSVファイルを検索（全ての .csv を対象）
                pattern = str(self.downloads_folder / "*.csv")
                files = glob.glob(pattern)
                
                for file_path in files:
                    path = Path(file_path)
                    
                    # .crdownload などの一時ファイルは除外
                    if path.suffix.lower() != ".csv":
                        continue
                    
                    # ファイルロックが解除されているか確認
                    if not is_file_locked(path):
                        logger.success(f"ダウンロード完了: {path}")
                        return path
                
                time_module.sleep(1)
            
            logger.warning(f"ダウンロードタイムアウト (試行 {attempt + 1}/{max_retries})")
        
        logger.error(f"ダウンロードが全リトライで失敗しました ({max_retries}回試行)")
        return None



class TaskRunner:
    """タスク実行を管理するクラス"""
    
    def __init__(self, progress_callback=None):
        """
        Args:
            progress_callback: 進捗通知用コールバック関数
                              (current: int, total: int, message: str) -> None
        """
        self.excel_handler = ExcelHandler()
        self.download_handler = DownloadHandler()
        self.progress_callback = progress_callback
        self.stop_requested = False  # 中断フラグ
        self.paused = False         # 一時停止フラグ
        self.current_workbook_path = None  # 現在開いているワークブックのパス（close_after用）

    def request_stop(self):
        """中断をリクエスト"""
        self.stop_requested = True
        logger.info("中断リクエストを受信しました")

    def pause(self):
        """一時停止"""
        self.paused = True
        logger.info("一時停止リクエスト: ON")

    def resume(self):
        """再開"""
        self.paused = False
        logger.info("一時停止リクエスト: OFF")
    
    def set_progress_callback(self, callback):
        """進捗コールバックを設定"""
        self.progress_callback = callback
    
    def _notify_progress(self, current: int, total: int, message: str):
        """進捗を通知"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def check_time(self, task: TaskConfig, force: bool = False) -> bool:
        """
        実行可能時間かチェックし、必要に応じて待機する
        
        - 現在時刻がセッション内（start_time〜end_time）なら即座に実行
        - 現在時刻がstart_timeより前なら、start_timeまで待機してから実行
        - 現在時刻がend_timeを過ぎていたらスキップ
        
        待機中はユーザーによる中断リクエストにも対応する
        """
        if force:
            logger.info(f"強制実行モード: 時間チェックをスキップ ({task.start_time_str()})")
            return True
            
        now = datetime.now()
        now_time = now.time()
        
        # 既にセッション内であれば即座に実行
        if task.is_within_session(now):
            return True
        
        # 深夜またぎ対応: start_time > end_time の場合
        if task.start_time > task.end_time:
            # 深夜またぎの場合は、now_time < start_time かつ now_time > end_time なら「待機」
            # それ以外（すでにセッション内）は上でTrueを返している
            if now_time > task.end_time and now_time < task.start_time:
                # 待機すべき（start_timeまで待つ）
                pass
            else:
                # すでに終了（end_time以降かつstart_time前ではない = セッション外）
                logger.warning(f"スキップ: 実行可能時間外です ({task.start_time.strftime('%H:%M')} - {task.end_time.strftime('%H:%M')})")
                return False
        else:
            # 通常の時間帯 (start_time <= end_time)
            if now_time > task.end_time:
                # 終了時刻を過ぎている → スキップ
                logger.warning(f"スキップ: 実行可能時間を過ぎています ({task.start_time.strftime('%H:%M')} - {task.end_time.strftime('%H:%M')})")
                return False
            elif now_time < task.start_time:
                # 開始時刻より前 → 待機する
                pass
        
        # ここに来た場合は、start_timeまで待機する
        wait_until = datetime.combine(now.date(), task.start_time)
        
        # 深夜またぎで、現在時刻がstart_timeより後（例: 今23:00でstart_time=22:00）の場合は翌日ではない
        # 現在時刻がstart_timeより前の場合のみ待機対象
        if now > wait_until:
            # すでにstart_timeを過ぎているがis_within_sessionがFalseだった
            # → end_timeを過ぎているケース（上で処理済み）なのでここには来ないはず
            logger.warning(f"スキップ: 実行可能時間外です ({task.start_time.strftime('%H:%M')} - {task.end_time.strftime('%H:%M')})")
            return False
        
        # 待機開始
        wait_seconds = (wait_until - now).total_seconds()
        wait_minutes = int(wait_seconds / 60)
        
        logger.info(f"待機開始: {task.start_time.strftime('%H:%M')} まで約 {wait_minutes} 分待機します")
        self._notify_progress(0, 1, f"待機中: {task.start_time.strftime('%H:%M')} まで約 {wait_minutes} 分")
        
        # 1分ごとにチェックしながら待機
        while datetime.now() < wait_until:
            # 中断リクエストのチェック
            if self.stop_requested:
                logger.warning("待機中にユーザーにより中断されました")
                return False
            
            # 一時停止中も待機を継続（ただしログする）
            if self.paused:
                self._notify_progress(0, 1, f"一時停止中（待機も一時停止）: {task.start_time.strftime('%H:%M')} 待ち")
            
            # 残り時間を更新
            remaining = (wait_until - datetime.now()).total_seconds()
            remaining_minutes = int(remaining / 60)
            if remaining_minutes > 0 and not self.paused:
                self._notify_progress(0, 1, f"待機中: {task.start_time.strftime('%H:%M')} まで残り {remaining_minutes} 分")
            
            # 60秒待機（残り時間が60秒未満なら残り時間だけ待機）
            sleep_time = min(60, max(1, remaining))
            time_module.sleep(sleep_time)
        
        logger.info(f"待機完了: {task.start_time.strftime('%H:%M')} になりました。タスクを開始します。")
        return True
    
    def run_task(self, task: TaskConfig, task_num: int = 1, total_tasks: int = 1, force: bool = False) -> bool:
        """
        単一タスクを実行
        
        Args:
            task: 実行するタスク設定
            task_num: 現在のタスク番号
            total_tasks: 総タスク数
            force: 時間チェックをスキップするか
            
        Returns:
            成功した場合True
        """
        file_name = Path(task.file_path).name
        self._notify_progress(task_num, total_tasks, f"開始: {file_name}")
        logger.info(f"タスク開始: {task.file_path}")
        
        # タスク開始時刻を記録
        task_start = time_module.time()
        
        # 時刻チェック
        if not self.check_time(task, force):
            return False
        
        try:
            # Excel起動（既に起動済みの場合は再利用）
            self._notify_progress(task_num, total_tasks, f"Excel起動中: {file_name}")
            if not self.excel_handler.start_excel(visible=True):
                return False
            
            # ワークブックを開く（close_after対応: 同じファイルなら再利用）
            need_open_workbook = True
            if self.current_workbook_path == task.file_path and self.excel_handler.workbook is not None:
                # 同じファイルが既に開いている
                logger.info(f"ワークブックを再利用します: {file_name}")
                need_open_workbook = False
            else:
                # 前のワークブックが開いていれば閉じる
                if self.excel_handler.workbook is not None:
                    self.excel_handler.close_workbook(save=False)
            
            if need_open_workbook:
                self._notify_progress(task_num, total_tasks, f"ファイルを開いています: {file_name}")
                if not self.excel_handler.open_workbook(task.file_path):
                    self.excel_handler.quit_excel()
                    return False
                self.current_workbook_path = task.file_path
            
            # ダウンロード処理（skip_downloadがFalseの場合のみ）
            csv_path = None
            if not task.skip_download:
                # 既存CSVの削除
                if not self.download_handler.cleanup_existing_csv(task.search_key):
                    if task.close_after:
                        self.excel_handler.close_workbook()
                        self.excel_handler.quit_excel()
                        self.current_workbook_path = None
                    return False
                
                # ダウンロードをトリガー
                self._notify_progress(task_num, total_tasks, f"ダウンロード中: {task.search_key}")
                if not self.download_handler.trigger_download(task.download_url):
                    if task.close_after:
                        self.excel_handler.close_workbook()
                        self.excel_handler.quit_excel()
                        self.current_workbook_path = None
                    return False
                
                # ダウンロード待機
                self._notify_progress(task_num, total_tasks, f"ダウンロード待機中: {task.search_key}")
                csv_path = self.download_handler.wait_for_download(task.search_key)
                if csv_path is None:
                    logger.error("ダウンロードに失敗しました")
                    if task.close_after:
                        self.excel_handler.close_workbook()
                        self.excel_handler.quit_excel()
                        self.current_workbook_path = None
                    return False
                
                # データ貼り付け
                self._notify_progress(task_num, total_tasks, f"データ転記中: {task.target_sheet}")
                if not self.excel_handler.paste_data_to_sheet(task.target_sheet, csv_path):
                    if task.close_after:
                        self.excel_handler.close_workbook()
                        self.excel_handler.quit_excel()
                        self.current_workbook_path = None
                    safe_delete_file(csv_path)
                    return False
                
                # CSVを削除
                safe_delete_file(csv_path)
            else:
                # ダウンロードスキップ時はファイルを開くのみ
                logger.info(f"ダウンロードをスキップしました: {file_name}")
                self._notify_progress(task_num, total_tasks, f"ファイルを開きました: {file_name}")
            
            # ▼ マクロ実行（ActionAfter処理の前）
            if task.macro_name:
                self._notify_progress(task_num, total_tasks, f"マクロ実行中: {task.macro_name}")
                if not self.excel_handler.run_macro(task.macro_name):
                    # マクロ失敗で止めるかは要件によるが、ここではログだけ出して続行する
                    # （失敗したら意味ない場合は return False にする）
                    show_warning("マクロエラー", f"マクロ '{task.macro_name}' の実行に失敗しました。\n処理を続行しますが、結果を確認してください。")
            
            # ActionAfter処理
            action = task.action_after.upper()
            if action == "PAUSE":
                # 一時停止してユーザーに手動作業を促す
                self._notify_progress(task_num, total_tasks, f"手動作業待ち: {file_name}")
                
                try:
                    # カスタムポップアップメッセージがあれば使用
                    if task.popup_message:
                        popup_msg = task.popup_message
                    else:
                        popup_msg = (
                            f"手動作業を行ってください。\n\n"
                            f"ファイル: {task.file_path}\n"
                            f"シート: {task.target_sheet}\n\n"
                            f"作業完了後、OKを押してください。"
                        )
                    show_info("Co-worker Bot - 手動作業", popup_msg)
                    
                    # OK押下後に保存
                    # 注意: ここでエラーが出ても、ユーザー作業は完了しているのでタスクは成功扱いとする
                    try:
                        if self.excel_handler.workbook:
                            self.excel_handler.save_workbook()
                    except Exception as save_err:
                        logger.warning(f"PAUSE後の保存に失敗しましたが、続行します: {save_err}")
                        
                except Exception as e:
                    logger.error(f"PAUSE処理中のエラー: {e}")
                    # PAUSE自体はユーザー介入なので、ここでエラーが出ても続行可能な場合は成功としたいが、
                    # 致命的なエラーの可能性もあるため、ログには残す。
                    # ただし「作業完了」の意志は示されたのでTrueで抜ける設計にする
                    pass
            elif action == "NONE" or action == "":
                # 何もしない（保存しない）
                logger.info(f"ActionAfter=NONE: 保存せずに続行します")
                self._notify_progress(task_num, total_tasks, f"完了（保存なし）: {file_name}")
            else:
                # Save（デフォルト）: 自動保存
                self._notify_progress(task_num, total_tasks, f"保存中: {file_name}")
                self.excel_handler.save_workbook()
            
            # ワークブックを閉じる（close_afterの場合）
            if task.close_after:
                self.excel_handler.close_workbook()
                self.excel_handler.quit_excel()
                self.current_workbook_path = None
            else:
                logger.info(f"ワークブックを開いたままにします: {file_name}")
            
            self._notify_progress(task_num, total_tasks, f"完了: {file_name}")
            
            # タスク所要時間を計算・ログ
            task_elapsed = time_module.time() - task_start
            elapsed_str = f"{int(task_elapsed // 60):02d}:{int(task_elapsed % 60):02d}"
            logger.success(f"タスク完了: {task.file_path} (所要時間: {elapsed_str})")
            return True
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}\n{traceback.format_exc()}")
            if task.close_after:
                self.excel_handler.close_workbook()
                self.excel_handler.quit_excel()
                self.current_workbook_path = None
            return False
    
    def run_group(self, tasks: List[TaskConfig], force: bool = False) -> dict:
        """
        グループ内の全タスクを順次実行
        
        Args:
            tasks: 実行するタスクのリスト（最適化済みを推奨）
            force: 時間チェックをスキップするか
            
        Returns:
            実行結果の辞書 {"success": int, "failed": int, "skipped": int}
        """
        results = {"success": 0, "failed": 0, "skipped": 0}
        total_tasks = len(tasks)
        self.stop_requested = False  # フラグ初期化
        
        mode_str = " (強制実行)" if force else ""
        logger.info(f"グループ実行開始{mode_str}: {total_tasks} 件のタスク")
        self._notify_progress(0, total_tasks, f"グループ実行{mode_str}: {total_tasks} 件")
        
        for i, task in enumerate(tasks, 1):
            # 中断チェック
            if self.stop_requested:
                logger.warning("ユーザーにより中断されました")
                self._notify_progress(i-1, total_tasks, "中断されました")
                break
            
            # 一時停止待機ループ
            while self.paused:
                self._notify_progress(i-1, total_tasks, "一時停止中... (再開待ち)")
                time_module.sleep(0.5)
                # 待機中に中断指示が来ることも考慮
                if self.stop_requested:
                    break
            
            # 再度中断チェック（ループ抜け直後）
            if self.stop_requested:
                logger.warning("ユーザーにより中断されました")
                self._notify_progress(i-1, total_tasks, "中断されました")
                break
                
            logger.info(f"=== タスク {i}/{total_tasks} ===")
            
            # 次のタスクが同じファイルかチェック（スマートclose_after）
            next_task = tasks[i] if i < total_tasks else None
            is_last_for_this_file = (
                next_task is None or 
                next_task.file_path != task.file_path
            )
            
            # close_afterを一時的に制御
            original_close_after = task.close_after
            if not is_last_for_this_file and task.close_after:
                logger.info(f"次も同じファイルのため、close_afterをスキップします")
                task.close_after = False
            
            # 日付条件チェック（曜日・祝日・日付）
            should_skip, skip_reason = should_skip_task(
                task.weekdays, task.skip_holiday, task.date_condition
            )
            if should_skip:
                results["skipped"] += 1
                self._notify_progress(i, total_tasks, f"スキップ({skip_reason}): {Path(task.file_path).name}")
                logger.info(f"日付条件スキップ: {skip_reason}")
                task.close_after = original_close_after  # 復元
                continue
            
            if not self.check_time(task, force):
                results["skipped"] += 1
                self._notify_progress(i, total_tasks, f"スキップ: {Path(task.file_path).name}")
                task.close_after = original_close_after  # 復元
                continue
            
            if self.run_task(task, i, total_tasks, force):
                results["success"] += 1
            else:
                results["failed"] += 1
            
            task.close_after = original_close_after  # 復元
        
        # グループ終了時のクリーンアップ
        # タスク個別の CloseAfter 設定を尊重するため、ここでは強制クローズしない
        if self.excel_handler.workbook is not None:
            logger.info("ワークブックを開いたまま終了します（CloseAfter設定に従います）")
        
        self._notify_progress(total_tasks, total_tasks, "全タスク完了")
        logger.info(
            f"グループ実行完了: 成功={results['success']}, "
            f"失敗={results['failed']}, スキップ={results['skipped']}"
        )
        
        return results

