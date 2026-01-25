
import unittest
from datetime import time, datetime, timedelta
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config_loader import TaskConfig

class TestTaskConfig(unittest.TestCase):
    
    def test_is_within_session_normal(self):
        """通常時間帯（日中）のテスト"""
        # 09:00 - 17:00
        task = TaskConfig(
            group="Test", start_time=time(9, 0), end_time=time(17, 0),
            file_path="", target_sheet="", search_key="", download_url="",
            action_after="", active=True,
            skip_download=False, close_after=False, popup_message=""
        )
        
        # 範囲内
        self.assertTrue(task.is_within_session(datetime(2023, 1, 1, 12, 0)))
        self.assertTrue(task.is_within_session(datetime(2023, 1, 1, 9, 0)))
        self.assertTrue(task.is_within_session(datetime(2023, 1, 1, 17, 0)))
        
        # 範囲外
        self.assertFalse(task.is_within_session(datetime(2023, 1, 1, 8, 59)))
        self.assertFalse(task.is_within_session(datetime(2023, 1, 1, 17, 1)))

    def test_is_within_session_midnight(self):
        """深夜またぎのテスト"""
        # 22:00 - 05:00
        task = TaskConfig(
            group="Test", start_time=time(22, 0), end_time=time(5, 0),
            file_path="", target_sheet="", search_key="", download_url="",
            action_after="", active=True,
            skip_download=False, close_after=False, popup_message=""
        )
        
        # 範囲内
        self.assertTrue(task.is_within_session(datetime(2023, 1, 1, 23, 0)))  # 当日夜
        self.assertTrue(task.is_within_session(datetime(2023, 1, 2, 2, 0)))   # 翌日早朝
        self.assertTrue(task.is_within_session(datetime(2023, 1, 1, 22, 0)))
        self.assertTrue(task.is_within_session(datetime(2023, 1, 2, 5, 0)))
        
        # 範囲外
        self.assertFalse(task.is_within_session(datetime(2023, 1, 1, 21, 59)))
        self.assertFalse(task.is_within_session(datetime(2023, 1, 1, 5, 1)))
        self.assertFalse(task.is_within_session(datetime(2023, 1, 1, 12, 0)))

    def test_from_row_parsing_valid(self):
        """from_rowの正常系パーステスト"""
        row = pd.Series({
            "Group": "A",
            "StartTime": "09:30",
            "EndTime": "18:00",
            "FilePath": "test.xlsx",
            "Active": 1
        })
        task = TaskConfig.from_row(row)
        self.assertEqual(task.start_time, time(9, 30))
        self.assertEqual(task.end_time, time(18, 0))

    def test_from_row_parsing_invalid(self):
        """from_rowの異常系パーステスト（エラーにならずデフォルト値になるか確認）"""
        # 不正な時刻フォーマット
        row = pd.Series({
            "Group": "A",
            "StartTime": "invalid",
            "EndTime": "18:00",
            "Active": 1
        })
        
        # エラーにならず、デフォルト値(00:00)が返ることを期待
        task = TaskConfig.from_row(row)
        self.assertEqual(task.start_time, time(0, 0))
        
        # コロン区切り以外の異常値
        row2 = pd.Series({
            "Group": "A",
            "StartTime": "12;30",  # セミコロン（実装で置換対応したので成功するはず）
            "EndTime": "18:00",
            "Active": 1
        })
        task2 = TaskConfig.from_row(row2)
        self.assertEqual(task2.start_time, time(12, 30))


if __name__ == '__main__':
    unittest.main()
