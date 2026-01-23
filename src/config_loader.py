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
    
    def start_time_str(self) -> str:
        """StartTimeを文字列で返す（HH:MM形式）"""
        return self.start_time.strftime("%H:%M")
    
    @classmethod
    def from_row(cls, row: pd.Series) -> "TaskConfig":
        """DataFrameの行からTaskConfigを生成"""
        # StartTimeの変換
        start_time_val = row.get("StartTime", "00:00")
        if pd.isna(start_time_val):
            start_time = time(0, 0)
        elif isinstance(start_time_val, str):
            parts = start_time_val.split(":")
            start_time = time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        elif hasattr(start_time_val, 'hour'):
            start_time = time(start_time_val.hour, start_time_val.minute)
        else:
            start_time = time(0, 0)
        
        return cls(
            group=str(row.get("Group", "")),
            start_time=start_time,
            file_path=str(row.get("FilePath", "")),
            target_sheet=str(row.get("TargetSheet", "")),
            search_key=str(row.get("SearchKey", "")),
            download_url=str(row.get("DownloadURL", "")),
            action_after=str(row.get("ActionAfter", "Save")),
            active=bool(row.get("Active", False))
        )


class ConfigLoader:
    """設定マスタファイルの読み込みクラス"""
    
    DEFAULT_MASTER_FILE = "Task_Master.xlsx"
    SHEET_NAME = "TaskList"
    
    def __init__(self, master_path: Optional[Path] = None):
        """
        Args:
            master_path: マスタファイルのパス。Noneの場合は同階層から読み込む
        """
        if master_path is None:
            # 実行ファイルと同階層のsettingsフォルダを探す
            import sys
            if getattr(sys, 'frozen', False):
                base_path = Path(sys.executable).parent
            else:
                base_path = Path(__file__).parent.parent
            
            self.master_path = base_path / "settings" / self.DEFAULT_MASTER_FILE
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


# テスト用
if __name__ == "__main__":
    loader = ConfigLoader()
    print("Groups:", loader.get_groups())
    print("StartTimes:", [t.strftime("%H:%M") for t in loader.get_start_times()])
    
    for group in loader.get_groups():
        print(f"\n=== {group} ===")
        for task in loader.get_tasks_by_group(group):
            print(f"  - {task.start_time_str()} {task.file_path} -> {task.target_sheet}")

