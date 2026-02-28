# -*- coding: utf-8 -*-
"""
kai_system - 通知モジュール
クロスプラットフォーム対応のデスクトップ通知 + Webhook通知を提供する
"""

import json
import platform
import subprocess
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

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
        title = "kai_system - 完了（エラーあり）"
    else:
        title = "kai_system - 完了"

    message = (
        f"成功: {success_count}件 / 失敗: {failed_count}件 / スキップ: {skipped_count}件\n"
        f"所要時間: {elapsed_time}"
    )

    show_toast_notification(title, message)


# ----------------------------------------------------------------
# Webhook 通知 (Slack / Discord)
# ----------------------------------------------------------------

def send_webhook(
    webhook_url: str,
    message: str,
    title: Optional[str] = None,
    color: Optional[str] = None,
) -> bool:
    """
    Webhook URL に通知を送信する（Slack / Discord 自動判別）

    Args:
        webhook_url: Webhook URL
        message: 通知メッセージ
        title: 通知タイトル（省略可）
        color: 色コード（例: "#36a64f"）

    Returns:
        成功した場合True
    """
    if not webhook_url:
        logger.warning("Webhook URL が設定されていません")
        return False

    try:
        if "discord" in webhook_url.lower():
            payload = _build_discord_payload(message, title, color)
        else:
            payload = _build_slack_payload(message, title, color)

        data = json.dumps(payload).encode("utf-8")
        req = Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            if resp.status < 300:
                logger.info(f"Webhook通知を送信しました: {title or message[:50]}")
                return True
            else:
                logger.warning(f"Webhook応答エラー: {resp.status}")
                return False

    except URLError as e:
        logger.error(f"Webhook送信失敗: {e}")
        return False
    except Exception as e:
        logger.error(f"Webhook送信エラー: {e}")
        return False


def _build_slack_payload(message: str, title: Optional[str], color: Optional[str]) -> dict:
    """Slack Incoming Webhook 用ペイロードを構築"""
    if title or color:
        attachment = {"text": message, "color": color or "#36a64f"}
        if title:
            attachment["title"] = title
        return {"attachments": [attachment]}
    else:
        return {"text": message}


def _build_discord_payload(message: str, title: Optional[str], color: Optional[str]) -> dict:
    """Discord Webhook 用ペイロードを構築"""
    if title or color:
        embed = {"description": message}
        if title:
            embed["title"] = title
        if color:
            # Discord は 10進数の色コードを使う
            hex_color = color.lstrip("#")
            try:
                embed["color"] = int(hex_color, 16)
            except ValueError:
                pass
        return {"embeds": [embed]}
    else:
        return {"content": message}


def notify_webhook_task_complete(
    webhook_url: str,
    action_name: str,
    success: bool,
    message: str = "",
    elapsed_time: str = "",
) -> bool:
    """タスク完了をWebhookで通知する"""
    if not webhook_url:
        return False

    if success:
        title = f"kai_system: {action_name} 完了"
        color = "#36a64f"  # 緑
    else:
        title = f"kai_system: {action_name} 失敗"
        color = "#ff0000"  # 赤

    body = message
    if elapsed_time:
        body += f"\n所要時間: {elapsed_time}"

    return send_webhook(webhook_url, body, title=title, color=color)
