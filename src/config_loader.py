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


@dataclass
class TaskConfig:
    """タスク設定を表すデータクラス"""
    group: str
    start_time: time
    file_path: str
    target_sheet: str
    search_key: str
    download_url: str
    action_after: str  # "Save" or "Pause"
    active: bool
    end_time: time
    skip_download: bool = False   # ダウンロードをスキップ（ファイルを開くのみ）
    close_after: bool = False      # TRUEでタスク完了後にファイルを閉じる（デフォルトは開いたまま）
    popup_message: str = ""        # カスタムポップアップメッセージ
    
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
        # StartTimeの変換
        start_time_val = row.get("StartTime", "00:00")
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
        end_time_val = row.get("EndTime")
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
        
        return cls(
            group=str(row.get("Group", "")),
            start_time=start_time,
            file_path=str(row.get("FilePath", "")),
            target_sheet=str(row.get("TargetSheet", "")),
            search_key=str(row.get("SearchKey", "")),
            download_url=str(row.get("DownloadURL", "")),
            action_after=str(row.get("ActionAfter", "Save")),
            active=bool(row.get("Active", False)),
            end_time=end_time,
            skip_download=bool(row.get("SkipDownload", False)),
            close_after=bool(row.get("CloseAfter", False)),
            popup_message=str(row.get("PopupMessage", "") if not pd.isna(row.get("PopupMessage")) else "")
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


# テスト用
if __name__ == "__main__":
    loader = ConfigLoader()
    print("Groups:", loader.get_groups())
    print("StartTimes:", [t.strftime("%H:%M") for t in loader.get_start_times()])
    
    for group in loader.get_groups():
        print(f"\n=== {group} ===")
        for task in loader.get_tasks_by_group(group):
            print(f"  - {task.start_time_str()} {task.file_path} -> {task.target_sheet}")

