# -*- coding: utf-8 -*-
"""
Co-worker Bot - ロボットロジックモジュール
Excel操作、ダウンロード処理、ファイル監視を行う
"""

import os
import time as time_module
import webbrowser
from datetime import datetime, time
from pathlib import Path
from typing import Optional, List
import glob

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
            self.excel_app.DisplayAlerts = False
            return True
        except Exception as e:
            logger.error(f"Excel起動エラー: {e}")
            return False
    
    def open_workbook(self, file_path: str) -> bool:
        """ワークブックを開く"""
        try:
            if not Path(file_path).exists():
                logger.error(f"ファイルが見つかりません: {file_path}")
                return False
            
            self.workbook = self.excel_app.Workbooks.Open(file_path)
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


class DownloadHandler:
    """ダウンロード処理を行うクラス"""
    
    def __init__(self, timeout: int = 60):
        self.downloads_folder = get_downloads_folder()
        self.timeout = timeout
    
    def cleanup_existing_csv(self, search_key: str) -> None:
        """既存の該当CSVファイルを削除（誤爆防止）"""
        pattern = str(self.downloads_folder / f"*{search_key}*.csv")
        for file_path in glob.glob(pattern):
            safe_delete_file(Path(file_path))
            logger.info(f"既存CSVを削除しました: {file_path}")
    
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
    
    def wait_for_download(self, search_key: str) -> Optional[Path]:
        """
        ダウンロードフォルダを監視し、CSVファイルの完了を待つ
        
        Args:
            search_key: ファイル名に含まれるキーワード
            
        Returns:
            ダウンロードされたファイルのパス、タイムアウト時はNone
        """
        logger.info(f"ダウンロード待機中... (キー: {search_key}, タイムアウト: {self.timeout}秒)")
        
        start_time = time_module.time()
        
        while time_module.time() - start_time < self.timeout:
            # CSVファイルを検索（厳密に .csv のみ）
            pattern = str(self.downloads_folder / f"*{search_key}*.csv")
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
        
        logger.error(f"ダウンロードがタイムアウトしました ({self.timeout}秒)")
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
    
    def set_progress_callback(self, callback):
        """進捗コールバックを設定"""
        self.progress_callback = callback
    
    def _notify_progress(self, current: int, total: int, message: str):
        """進捗を通知"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def check_time(self, task: TaskConfig) -> bool:
        """現在時刻がタスクの開始可能時刻以降かチェック"""
        now = datetime.now().time()
        if now < task.start_time:
            logger.skip(
                f"時間外のためスキップ: {task.group} "
                f"(現在: {now.strftime('%H:%M')}, 開始可能: {task.start_time.strftime('%H:%M')})"
            )
            return False
        return True
    
    def run_task(self, task: TaskConfig, task_num: int = 1, total_tasks: int = 1) -> bool:
        """
        単一タスクを実行
        
        Args:
            task: 実行するタスク設定
            task_num: 現在のタスク番号
            total_tasks: 総タスク数
            
        Returns:
            成功した場合True
        """
        file_name = Path(task.file_path).name
        self._notify_progress(task_num, total_tasks, f"開始: {file_name}")
        logger.info(f"タスク開始: {task.file_path}")
        
        # 時刻チェック
        if not self.check_time(task):
            return False
        
        try:
            # Excel起動
            self._notify_progress(task_num, total_tasks, f"Excel起動中: {file_name}")
            if not self.excel_handler.start_excel(visible=True):
                return False
            
            # ワークブックを開く（動的URL再計算のため）
            self._notify_progress(task_num, total_tasks, f"ファイルを開いています: {file_name}")
            if not self.excel_handler.open_workbook(task.file_path):
                self.excel_handler.quit_excel()
                return False
            
            # 既存CSVの削除
            self.download_handler.cleanup_existing_csv(task.search_key)
            
            # ダウンロードをトリガー
            self._notify_progress(task_num, total_tasks, f"ダウンロード中: {task.search_key}")
            if not self.download_handler.trigger_download(task.download_url):
                self.excel_handler.close_workbook()
                self.excel_handler.quit_excel()
                return False
            
            # ダウンロード待機
            self._notify_progress(task_num, total_tasks, f"ダウンロード待機中: {task.search_key}")
            csv_path = self.download_handler.wait_for_download(task.search_key)
            if csv_path is None:
                logger.error("ダウンロードに失敗しました")
                self.excel_handler.close_workbook()
                self.excel_handler.quit_excel()
                return False
            
            # データ貼り付け
            self._notify_progress(task_num, total_tasks, f"データ転記中: {task.target_sheet}")
            if not self.excel_handler.paste_data_to_sheet(task.target_sheet, csv_path):
                self.excel_handler.close_workbook()
                self.excel_handler.quit_excel()
                safe_delete_file(csv_path)
                return False
            
            # CSVを削除
            safe_delete_file(csv_path)
            
            # ActionAfter処理
            if task.action_after.upper() == "PAUSE":
                # 一時停止してユーザーに手動作業を促す
                self._notify_progress(task_num, total_tasks, f"手動作業待ち: {file_name}")
                show_info(
                    "Co-worker Bot - 手動作業",
                    f"手動作業を行ってください。\n\n"
                    f"ファイル: {task.file_path}\n"
                    f"シート: {task.target_sheet}\n\n"
                    f"作業完了後、OKを押してください。"
                )
                # OK押下後に保存
                self.excel_handler.save_workbook()
            else:
                # 自動保存
                self._notify_progress(task_num, total_tasks, f"保存中: {file_name}")
                self.excel_handler.save_workbook()
            
            # ワークブックを閉じる
            self.excel_handler.close_workbook()
            self.excel_handler.quit_excel()
            
            self._notify_progress(task_num, total_tasks, f"完了: {file_name}")
            logger.success(f"タスク完了: {task.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self.excel_handler.close_workbook()
            self.excel_handler.quit_excel()
            return False
    
    def run_group(self, tasks: List[TaskConfig]) -> dict:
        """
        グループ内の全タスクを順次実行
        
        Args:
            tasks: 実行するタスクのリスト
            
        Returns:
            実行結果の辞書 {"success": int, "failed": int, "skipped": int}
        """
        results = {"success": 0, "failed": 0, "skipped": 0}
        total_tasks = len(tasks)
        
        logger.info(f"グループ実行開始: {total_tasks} 件のタスク")
        self._notify_progress(0, total_tasks, f"グループ実行開始: {total_tasks} 件のタスク")
        
        for i, task in enumerate(tasks, 1):
            logger.info(f"=== タスク {i}/{total_tasks} ===")
            
            if not self.check_time(task):
                results["skipped"] += 1
                self._notify_progress(i, total_tasks, f"スキップ: {Path(task.file_path).name}")
                continue
            
            if self.run_task(task, i, total_tasks):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        self._notify_progress(total_tasks, total_tasks, "全タスク完了")
        logger.info(
            f"グループ実行完了: 成功={results['success']}, "
            f"失敗={results['failed']}, スキップ={results['skipped']}"
        )
        
        return results

