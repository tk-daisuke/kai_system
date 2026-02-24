# -*- coding: utf-8 -*-
"""
kai_system - 通知モジュール
クロスプラットフォーム対応のデスクトップ通知を提供する
"""

import platform
import subprocess
from infra.logger import logger


def show_toast_notification(title: str, message: str, duration: int = 5) -> bool:
    """
    デスクトップ通知を表示する（クロスプラットフォーム）

    Args:
        title: 通知タイトル
        message: 通知メッセージ
        duration: 表示時間（秒）

    Returns:
        成功した場合True
    """
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # osascript で通知
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            logger.info(f"通知を表示: {title}")
            return True

        elif system == "Windows":
            # PowerShell トースト通知
            title_escaped = title.replace("'", "''")
            message_escaped = message.replace("'", "''")

            ps_script = f"""
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
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("kai_system").Show($toast)
            """

            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=5,
            )
            logger.info(f"通知を表示: {title}")
            return True

        elif system == "Linux":
            subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                timeout=5,
            )
            logger.info(f"通知を表示: {title}")
            return True

    except Exception as e:
        logger.warning(f"通知の表示に失敗しました: {e}")

    return False


def notify_task_complete(
    success_count: int, failed_count: int, skipped_count: int, elapsed_time: str
) -> None:
    """タスク完了通知を表示する"""
    if failed_count > 0:
        title = "⚠ kai_system - 完了（エラーあり）"
    else:
        title = "✓ kai_system - 完了"

    message = (
        f"成功: {success_count}件 / 失敗: {failed_count}件 / スキップ: {skipped_count}件\n"
        f"所要時間: {elapsed_time}"
    )

    show_toast_notification(title, message)
