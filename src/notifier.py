# -*- coding: utf-8 -*-
"""
Co-worker Bot - 通知モジュール
タスク完了時のOS通知（トースト）を提供する
"""

import ctypes
from utils import logger


def show_toast_notification(title: str, message: str, duration: int = 5) -> bool:
    """
    Windowsトースト通知を表示する
    
    Args:
        title: 通知タイトル
        message: 通知メッセージ
        duration: 表示時間（秒）※現在未使用
        
    Returns:
        成功した場合True
    """
    try:
        # Windows 10+ のトースト通知
        # win10toastやplyerを使う方法もあるが、依存を増やさないため
        # シンプルなBalloon通知を使用
        
        # 方法1: PowerShell経由でトースト通知
        import subprocess
        
        # エスケープ処理
        title_escaped = title.replace("'", "''")
        message_escaped = message.replace("'", "''")
        
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title_escaped}</text>
                    <text id="2">{message_escaped}</text>
                </binding>
            </visual>
        </toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Co-worker Bot").Show($toast)
        '''
        
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=5
        )
        
        logger.info(f"トースト通知を表示: {title}")
        return True
        
    except Exception as e:
        logger.warning(f"トースト通知に失敗しました（フォールバック通知を使用）: {e}")
        
        # フォールバック: シンプルなメッセージボックス（非モーダル風に）
        try:
            # MB_ICONINFORMATION | MB_SYSTEMMODAL
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x40 | 0x1000)
            return True
        except:
            return False


def notify_task_complete(success_count: int, failed_count: int, skipped_count: int, elapsed_time: str) -> None:
    """
    タスク完了通知を表示する
    
    Args:
        success_count: 成功件数
        failed_count: 失敗件数
        skipped_count: スキップ件数
        elapsed_time: 所要時間（文字列）
    """
    if failed_count > 0:
        title = "⚠ Co-worker Bot - 完了（エラーあり）"
    else:
        title = "✓ Co-worker Bot - 完了"
    
    message = (
        f"成功: {success_count}件 / 失敗: {failed_count}件 / スキップ: {skipped_count}件\n"
        f"所要時間: {elapsed_time}"
    )
    
    show_toast_notification(title, message)
