# -*- coding: utf-8 -*-
"""
Co-worker Bot - ユーティリティモジュール
ログ出力、共通関数を提供する
"""

import os
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Optional


# ダウンロードフォルダのパス（カスタム設定可能）
_CUSTOM_DOWNLOADS_FOLDER: Optional[Path] = None


def set_downloads_folder(path: str) -> None:
    """ダウンロードフォルダのパスを設定する"""
    global _CUSTOM_DOWNLOADS_FOLDER
    _CUSTOM_DOWNLOADS_FOLDER = Path(path)


def get_downloads_folder() -> Path:
    """
    Downloadsフォルダのパスを取得する
    
    優先順位:
    1. カスタム設定されたパス
    2. WindowsのKnown Folders API
    3. 環境変数USERPROFILEからの推測
    """
    global _CUSTOM_DOWNLOADS_FOLDER
    
    # カスタム設定があればそれを使用
    if _CUSTOM_DOWNLOADS_FOLDER and _CUSTOM_DOWNLOADS_FOLDER.exists():
        return _CUSTOM_DOWNLOADS_FOLDER
    
    # Windows Known Folders APIで取得を試行
    try:
        import ctypes.wintypes
        from ctypes import windll, wintypes
        
        # FOLDERID_Downloads
        FOLDERID_Downloads = ctypes.c_char_p(b'{374DE290-123F-4565-9164-39C4925E467B}')
        
        # SHGetKnownFolderPath
        SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
        SHGetKnownFolderPath.restype = ctypes.c_long
        
        path_ptr = ctypes.c_wchar_p()
        result = SHGetKnownFolderPath(FOLDERID_Downloads, 0, None, ctypes.byref(path_ptr))
        
        if result == 0 and path_ptr.value:
            downloads_path = Path(path_ptr.value)
            windll.ole32.CoTaskMemFree(path_ptr)
            if downloads_path.exists():
                return downloads_path
    except Exception:
        pass
    
    # フォールバック: 既知のカスタムパスをチェック
    custom_paths = [
        Path(r"E:\document\ダウンロード"),
        Path(os.environ.get("USERPROFILE", "")) / "Downloads",
        Path(os.environ.get("USERPROFILE", "")) / "ダウンロード",
    ]
    
    for path in custom_paths:
        if path.exists():
            return path
    
    # 最終フォールバック
    return Path(os.environ["USERPROFILE"]) / "Downloads"


def get_log_folder() -> Path:
    """ログフォルダのパスを取得する（実行ファイルと同階層）"""
    # PyInstaller でexe化された場合を考慮
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent
    
    log_folder = base_path / "logs"
    log_folder.mkdir(exist_ok=True)
    return log_folder


import sys


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
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
        
        # コンソールにも出力
        print(log_line.strip())
    
    def info(self, message: str) -> None:
        """INFOレベルのログ"""
        self._write("INFO", message)
    
    def warning(self, message: str) -> None:
        """WARNINGレベルのログ"""
        self._write("WARNING", message)
    
    def error(self, message: str) -> None:
        """ERRORレベルのログ"""
        self._write("ERROR", message)
    
    def success(self, message: str) -> None:
        """SUCCESSレベルのログ"""
        self._write("SUCCESS", message)
    
    def skip(self, message: str) -> None:
        """SKIPレベルのログ"""
        self._write("SKIP", message)


# シングルトンインスタンス
logger = Logger()


def show_message_box(title: str, message: str, style: int = 0) -> int:
    """
    メッセージボックスを表示する（最前面表示）
    
    Args:
        title: タイトル
        message: メッセージ本文
        style: メッセージボックスのスタイル
            0 = OK
            1 = OK/Cancel
            4 = Yes/No
            
    Returns:
        ボタンの戻り値（1=OK, 2=Cancel, 6=Yes, 7=No）
    """
    # MB_TOPMOST (0x40000) を削除して、通常のウィンドウとして表示
    return ctypes.windll.user32.MessageBoxW(
        None, 
        message, 
        title, 
        style  # | 0x40000 を削除
    )


def show_info(title: str, message: str) -> None:
    """情報メッセージボックスを表示"""
    # MB_ICONINFORMATION = 0x40
    show_message_box(title, message, 0x40)


def show_warning(title: str, message: str) -> None:
    """警告メッセージボックスを表示"""
    # MB_ICONWARNING = 0x30
    show_message_box(title, message, 0x30)


def show_error(title: str, message: str) -> None:
    """エラーメッセージボックスを表示"""
    # MB_ICONERROR = 0x10
    show_message_box(title, message, 0x10)


def confirm_dialog(title: str, message: str) -> bool:
    """
    OK/Cancelの確認ダイアログを表示
    
    Returns:
        OKが押された場合True
    """
    # MB_OKCANCEL = 1, MB_ICONQUESTION = 0x20
    result = show_message_box(title, message, 1 | 0x20)
    return result == 1  # IDOK


def is_file_locked(filepath: Path) -> bool:
    """
    ファイルがロックされているかチェック
    
    Args:
        filepath: チェック対象のファイルパス
        
    Returns:
        ロックされている場合True
    """
    try:
        with open(filepath, "r+b"):
            return False
    except (IOError, PermissionError):
        return True


def safe_delete_file(filepath: Path) -> bool:
    """
    ファイルを安全に削除する
    
    Args:
        filepath: 削除対象のファイルパス
        
    Returns:
        削除成功した場合True
    """
    try:
        if filepath.exists():
            filepath.unlink()
            logger.info(f"ファイルを削除しました: {filepath}")
            return True
        return True
    except Exception as e:
        logger.error(f"ファイル削除に失敗しました: {filepath} - {e}")
        return False
