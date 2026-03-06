# -*- coding: utf-8 -*-
"""
kai_system - ログモジュール
クロスプラットフォーム対応のログ出力を提供する
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_base_path() -> Path:
    """実行ファイルのベースパスを取得"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent.parent


def get_log_folder() -> Path:
    """ログフォルダのパスを取得する"""
    log_folder = _get_base_path() / "logs"
    log_folder.mkdir(exist_ok=True)
    return log_folder


class Logger:
    """ログ出力クラス"""

    def __init__(self):
        self._log_file: Optional[Path] = None

    @property
    def log_file(self) -> Path:
        """今日のログファイルパスを取得"""
        today = datetime.now().strftime("%Y%m%d")
        return get_log_folder() / f"log_{today}.txt"

    def _write(self, level: str, message: str) -> None:
        """ログをファイルに書き込む"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass  # ログ書き込み自体の失敗は黙殺

        # コンソールにも出力
        print(log_line.strip())

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def success(self, message: str) -> None:
        self._write("SUCCESS", message)

    def skip(self, message: str) -> None:
        self._write("SKIP", message)


    def rotate_logs(self, max_days: int = 30) -> int:
        """古いログファイルを削除する。削除した件数を返す"""
        log_folder = get_log_folder()
        cutoff = datetime.now() - __import__("datetime").timedelta(days=max_days)
        cutoff_str = cutoff.strftime("%Y%m%d")
        deleted = 0
        for f in log_folder.glob("log_*.txt"):
            date_str = f.stem.replace("log_", "")
            if date_str < cutoff_str:
                try:
                    f.unlink()
                    deleted += 1
                except Exception:
                    pass
        return deleted


# シングルトンインスタンス
logger = Logger()
