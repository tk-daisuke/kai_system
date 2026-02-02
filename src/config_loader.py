# -*- coding: utf-8 -*-
"""
Co-worker Bot - 設定読み込みモジュール
Task_Master.xlsx からタスク設定を読み込む
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import time, datetime

from utils import logger
import win32com.client
import pythoncom


@dataclass
class TaskConfig:
    """タスク設定を表すデータクラス"""
    group: str
    start_time: time
    file_path: str
    target_sheet: str
    download_url: str
    action_after: str  # "Save", "Pause", or "None"（何もしない）
    active: bool
    end_time: time
    task_name: str = ""            # タスク名（任意の説明用）
    skip_download: bool = False   # ダウンロードをスキップ（ファイルを開くのみ）
    close_after: bool = False      # TRUEでタスク完了後にファイルを閉じる（デフォルトは開いたまま）
    popup_message: str = ""        # カスタムポップアップメッセージ
    macro_name: str = ""           # 実行するVBAマクロ名
    weekdays: str = ""             # 実行曜日（1=月〜7=日、カンマ区切り）
    skip_holiday: bool = False     # 祝日スキップ
    date_condition: str = ""       # 日付条件（1,15 = 毎月1日・15日、L = 月末）
    
    def start_time_str(self) -> str:
        """StartTimeを文字列で返す（HH:MM形式）"""
        return self.start_time.strftime("%H:%M")

    def is_within_session(self, current_time: datetime) -> bool:
        """現在時刻が実行可能セッション内か判定する（深夜またぎ対応）"""
        now_time = current_time.time()
        
        # StartTime <= EndTime の場合（通常の時間帯：08:00 - 17:00など）
        if self.start_time <= self.end_time:
            return self.start_time <= now_time <= self.end_time
        
        # StartTime > EndTime の場合（深夜またぎ：22:00 - 05:00など）
        # 「StartTime以降」または「EndTime以前」であればセッション内
        return now_time >= self.start_time or now_time <= self.end_time
    
    @classmethod
    def from_row(cls, row: pd.Series) -> "TaskConfig":
        """DataFrameの行からTaskConfigを生成"""
        
        # カラム名のエイリアス定義（英語と日本語のゆれ対応）
        def get_val(keys: List[str], default: Any = None) -> Any:
            for key in keys:
                if key in row:
                    return row[key]
            return default

        # StartTimeの変換
        # 日本語ヘッダーを優先
        start_time_val = get_val(["開始時刻", "開始", "StartTime"], "00:00")
        start_time = time(0, 0)
        
        try:
            if pd.isna(start_time_val):
                start_time = time(0, 0)
            elif isinstance(start_time_val, str):
                # "9:00", "09:00", "9", "09" などに対応
                parts = start_time_val.replace(";", ":").split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                # 時刻の範囲チェック
                hour = max(0, min(23, hour))
                minute = max(0, min(59, minute))
                start_time = time(hour, minute)
            elif hasattr(start_time_val, 'hour'):
                start_time = time(start_time_val.hour, start_time_val.minute)
        except Exception as e:
            logger.warning(f"StartTimeのパースに失敗しました (値: {start_time_val}): {e} -> 00:00とします")
            start_time = time(0, 0)
            
        # EndTimeの変換
        end_time_val = get_val(["終了時刻", "終了", "EndTime"])
        end_time = None
        
        try:
            if not (pd.isna(end_time_val) or end_time_val == ""):
                if isinstance(end_time_val, str):
                    parts = end_time_val.replace(";", ":").split(":")
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    # 時刻の範囲チェック
                    hour = max(0, min(23, hour))
                    minute = max(0, min(59, minute))
                    end_time = time(hour, minute)
                elif hasattr(end_time_val, 'hour'):
                    end_time = time(end_time_val.hour, end_time_val.minute)
        except Exception as e:
            logger.warning(f"EndTimeのパースに失敗しました (値: {end_time_val}): {e} -> 自動設定を使用します")
            end_time = None

        if end_time is None:
            # EndTimeがない、またはエラーの場合はStartTimeの8時間後に設定（日付またぎ考慮）
            dummy_dt = datetime.combine(datetime.today(), start_time)
            from datetime import timedelta
            end_dt = dummy_dt + timedelta(hours=8)
            end_time = end_dt.time()
        
        # 各値の取得（日本語優先）
        group = str(get_val(["グループ", "Group"], ""))
        task_name_val = get_val(["タスク名", "TaskName", "Memo", "メモ"], "")
        task_name = str(task_name_val) if not pd.isna(task_name_val) else ""
        file_path = str(get_val(["ファイルパス", "ファイル", "FilePath"], ""))
        target_sheet = str(get_val(["CSV転記シート", "転記シート", "シート", "TargetSheet"], ""))
        download_url = str(get_val(["URL", "ダウンロードURL", "DownloadURL"], ""))
        action_after = str(get_val(["完了後動作", "動作", "ActionAfter"], "Save"))
        
        # Active (True/False or 1/0 or 有効/無効)
        active_val = get_val(["有効", "有効フラグ", "Active"], False)
        # "有効" などの日本語対応も含めるならここを拡張できるが、とりあえずbool変換が無難
        active = bool(active_val)
        
        skip_download = bool(get_val(["DLスキップ", "ダウンロードスキップ", "SkipDownload"], False))
        close_after = bool(get_val(["終了後閉じる", "閉じる", "CloseAfter"], False))
        
        popup_msg_val = get_val(["メッセージ", "ポップアップ", "PopupMessage"], "")
        popup_message = str(popup_msg_val) if not pd.isna(popup_msg_val) else ""
        
        macro_name_val = get_val(["マクロ名", "マクロ", "MacroName"], "")
        macro_name = str(macro_name_val) if not pd.isna(macro_name_val) else ""
        
        # 条件付き実行フィールド
        weekdays = str(get_val(["曜日", "Weekdays"], "")).strip()
        skip_holiday_val = get_val(["祝日スキップ", "SkipHoliday"], False)
        skip_holiday = skip_holiday_val is True or str(skip_holiday_val).upper() == "TRUE"
        date_condition = str(get_val(["日付条件", "DateCondition"], "")).strip()

        return cls(
            group=group,
            start_time=start_time,
            file_path=file_path,
            target_sheet=target_sheet,
            download_url=download_url,
            action_after=action_after,
            active=active,
            end_time=end_time,
            task_name=task_name,
            skip_download=skip_download,
            close_after=close_after,
            popup_message=popup_message,
            macro_name=macro_name,
            weekdays=weekdays,
            skip_holiday=skip_holiday,
            date_condition=date_condition
        )


class ConfigLoader:
    """設定マスタファイルの読み込みクラス"""
    
    DEFAULT_MASTER_FILE = "Task_Master.xlsx"
    SHEET_NAME = "TaskList"
    
    def __init__(self, master_path: Optional[Path] = None, env: str = "production"):
        """
        Args:
            master_path: マスタファイルのパス。Noneの場合は環境に応じたデフォルトパスを使用
            env: 実行環境 ("production" or "test")。master_pathが指定されていない場合に使用
        """
        if master_path is None:
            # 実行ファイルと同階層のsettingsフォルダを探す
            import sys
            if getattr(sys, 'frozen', False):
                base_path = Path(sys.executable).parent
            else:
                base_path = Path(__file__).parent.parent
            
            # 環境に応じたサブフォルダを選択
             # デフォルトは production（本番）
            if env == "test":
                sub_folder = "test"
            else:
                sub_folder = "production"
                
            self.master_path = base_path / "settings" / sub_folder / self.DEFAULT_MASTER_FILE
            
            # フォールバック: 指定環境になく、直下にある場合（旧仕様互換）
            if not self.master_path.exists():
                fallback_path = base_path / "settings" / self.DEFAULT_MASTER_FILE
                if fallback_path.exists():
                    self.master_path = fallback_path
                    
        else:
            self.master_path = Path(master_path)

    def refresh_master_file(self) -> bool:
        """
        マスタファイルをExcelで開いて保存し、関数（TODAYなど）を更新する
        """
        if not self.master_path.exists():
            return False
            
        logger.info(f"マスタファイルの値を更新中: {self.master_path.name}")
        excel = None
        workbook = None
        
        try:
            # COM初期化
            pythoncom.CoInitialize()
            
            # Excel起動
            try:
                # 既存のインスタンスをつかむとユーザーの邪魔になる可能性があるので
                # 新規インスタンスで裏でこっそりやる
                excel = win32com.client.DispatchEx("Excel.Application")
            except:
                excel = win32com.client.Dispatch("Excel.Application")
                
            excel.Visible = False
            excel.DisplayAlerts = False
            
            # 開く -> 更新 -> 保存
            workbook = excel.Workbooks.Open(str(self.master_path))
            workbook.Save()
            
            logger.info("マスタファイルの値を更新しました")
            return True
            
        except Exception as e:
            logger.warning(f"マスタファイルの更新に失敗しました（読み込みは続行します）: {e}")
            return False
            
        finally:
            if workbook:
                try: 
                    workbook.Close(SaveChanges=False) 
                except: pass
            if excel:
                try: 
                    excel.Quit() 
                except: pass
            # COM終了
            pythoncom.CoUninitialize()
    
    def load_tasks(self) -> List[TaskConfig]:
        """
        マスタファイルからタスク一覧を読み込む
        
        Returns:
            TaskConfigのリスト
        """
        if not self.master_path.exists():
            logger.error(f"マスタファイルが見つかりません: {self.master_path}")
            return []
        
        try:
            logger.info(f"マスタファイルを読み込み中: {self.master_path}")
            
            # Read Only でファイルを読み込む（排他制御対応）
            df = pd.read_excel(
                self.master_path,
                sheet_name=self.SHEET_NAME,
                engine="openpyxl"
            )
            
            tasks = []
            for _, row in df.iterrows():
                task = TaskConfig.from_row(row)
                if task.active:
                    tasks.append(task)
            
            logger.info(f"{len(tasks)} 件のアクティブなタスクを読み込みました")
            return tasks
            
        except Exception as e:
            logger.error(f"マスタファイル読み込みエラー: {e}")
            return []
    
    def get_groups(self) -> List[str]:
        """
        アクティブなグループ名の一覧を取得
        
        Returns:
            ユニークなグループ名のリスト
        """
        tasks = self.load_tasks()
        groups = list(dict.fromkeys([t.group for t in tasks]))  # 順序を保持しつつユニーク化
        return groups
    
    def get_start_times(self) -> List[time]:
        """
        アクティブなStartTime一覧を取得（ソート済み）
        
        Returns:
            ユニークなStartTimeのリスト（時刻順）
        """
        tasks = self.load_tasks()
        start_times = list(dict.fromkeys([t.start_time for t in tasks]))
        return sorted(start_times)
    
    def get_tasks_by_group(self, group_name: str) -> List[TaskConfig]:
        """
        指定グループのタスク一覧を取得
        
        Args:
            group_name: グループ名
            
        Returns:
            該当グループのTaskConfigリスト
        """
        tasks = self.load_tasks()
        return [t for t in tasks if t.group == group_name]
    
    def get_tasks_by_group_optimized(self, group_name: str) -> List[TaskConfig]:
        """
        指定グループのタスク一覧を取得（ファイルパスでグループ化して最適化）
        
        同じファイルパスを持つタスクを連続して配置し、
        ファイルの開き直しを最小化する
        
        Args:
            group_name: グループ名
            
        Returns:
            最適化されたTaskConfigリスト
        """
        tasks = [t for t in self.load_tasks() if t.group == group_name]
        
        if not tasks:
            return []
        
        # ファイルパスごとにグループ化
        from collections import OrderedDict
        file_groups: OrderedDict[str, List[TaskConfig]] = OrderedDict()
        
        for task in tasks:
            fp = task.file_path
            if fp not in file_groups:
                file_groups[fp] = []
            file_groups[fp].append(task)
        
        # 各ファイルグループ内を開始時刻順でソート
        optimized_tasks = []
        for file_path, group_tasks in file_groups.items():
            # 時刻順にソート
            sorted_tasks = sorted(group_tasks, key=lambda t: t.start_time)
            optimized_tasks.extend(sorted_tasks)
        
        logger.info(f"タスク最適化: {len(tasks)}件 → {len(file_groups)}ファイル")
        return optimized_tasks
    
    def get_tasks_by_start_time(self, start_time: time) -> List[TaskConfig]:
        """
        指定StartTimeのタスク一覧を取得
        
        Args:
            start_time: 開始時刻
            
        Returns:
            該当StartTimeのTaskConfigリスト
        """
        tasks = self.load_tasks()
        return [t for t in tasks if t.start_time == start_time]
    
    def get_tasks_from_start_time(self, start_time: time) -> List[TaskConfig]:
        """
        指定StartTime以降のタスク一覧を取得
        
        Args:
            start_time: 開始時刻
            
        Returns:
            該当StartTime以降のTaskConfigリスト（時刻順）
        """
        tasks = self.load_tasks()
        filtered = [t for t in tasks if t.start_time >= start_time]
        return sorted(filtered, key=lambda t: t.start_time)

    def get_all_tasks_sorted(self) -> List[TaskConfig]:
        """
        全タスクを時刻順にソートして取得
        
        Returns:
            時刻順のTaskConfigリスト
        """
        tasks = self.load_tasks()
        return sorted(tasks, key=lambda t: (t.start_time, t.group))

    def validate_tasks(self) -> List[dict]:
        """
        タスク設定のバリデーションを行う
        
        Returns:
            問題のあるタスクのリスト [{task: TaskConfig, issues: List[str]}]
        """
        tasks = self.load_tasks()
        issues_list = []
        
        for task in tasks:
            issues = []
            
            # ファイルパスの存在チェック
            if task.file_path:
                if not Path(task.file_path).exists():
                    issues.append(f"ファイルが見つかりません: {task.file_path}")
            else:
                issues.append("ファイルパスが空です")
            
            # URL チェック（ダウンロードスキップでなければ必須）
            if not task.skip_download:
                if not task.download_url:
                    issues.append("ダウンロードURLが空です")
                elif not task.download_url.startswith(("http://", "https://")):
                    issues.append(f"不正なURL形式: {task.download_url}")
            
            # シート名チェック
            if not task.skip_download and not task.target_sheet:
                issues.append("転記シート名が空です")
            
            if issues:
                issues_list.append({
                    "task": task,
                    "issues": issues
                })
        
        if issues_list:
            logger.warning(f"設定にエラーのあるタスク: {len(issues_list)} 件")
        else:
            logger.info("全タスクの設定チェック: OK")
        
        return issues_list


# テスト用
if __name__ == "__main__":
    loader = ConfigLoader()
    print("Groups:", loader.get_groups())
    print("StartTimes:", [t.strftime("%H:%M") for t in loader.get_start_times()])
    
    for group in loader.get_groups():
        print(f"\n=== {group} ===")
        for task in loader.get_tasks_by_group(group):
            print(f"  - {task.start_time_str()} {task.file_path} -> {task.target_sheet}")

