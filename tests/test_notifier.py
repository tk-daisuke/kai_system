# -*- coding: utf-8 -*-
"""notifier.py Webhook のユニットテスト"""
from unittest.mock import MagicMock, patch

from infra.notifier import (
    _build_slack_payload,
    _build_discord_payload,
    send_webhook,
    notify_webhook_task_complete,
)


class TestSlackPayload:

    def test_simple_message(self):
        p = _build_slack_payload("hello", None, None)
        assert p == {"text": "hello"}

    def test_with_title_and_color(self):
        p = _build_slack_payload("msg", "Title", "#ff0000")
        assert "attachments" in p
        assert p["attachments"][0]["title"] == "Title"
        assert p["attachments"][0]["color"] == "#ff0000"
        assert p["attachments"][0]["text"] == "msg"


class TestDiscordPayload:

    def test_simple_message(self):
        p = _build_discord_payload("hello", None, None)
        assert p == {"content": "hello"}

    def test_with_title_and_color(self):
        p = _build_discord_payload("msg", "Title", "#36a64f")
        assert "embeds" in p
        assert p["embeds"][0]["title"] == "Title"
        assert p["embeds"][0]["description"] == "msg"
        assert p["embeds"][0]["color"] == 0x36a64f


class TestSendWebhook:

    @patch("infra.notifier.urlopen")
    def test_slack_webhook(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = send_webhook("https://hooks.slack.com/services/xxx", "test")
        assert result is True

    @patch("infra.notifier.urlopen")
    def test_discord_webhook(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = send_webhook("https://discord.com/api/webhooks/xxx", "test")
        assert result is True

    def test_empty_url(self):
        result = send_webhook("", "test")
        assert result is False

    @patch("infra.notifier.urlopen", side_effect=Exception("network error"))
    def test_network_error(self, mock_urlopen):
        result = send_webhook("https://hooks.slack.com/xxx", "test")
        assert result is False


class TestNotifyWebhookTaskComplete:

    def test_empty_url_returns_false(self):
        assert notify_webhook_task_complete("", "test", True) is False

    @patch("infra.notifier.send_webhook")
    def test_success_notification(self, mock_send):
        mock_send.return_value = True
        result = notify_webhook_task_complete(
            "https://hooks.slack.com/xxx", "MyAction", True,
            "completed", "01:23"
        )
        assert result is True
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert "MyAction" in args[1]["title"] or "MyAction" in args.kwargs.get("title", "")

    @patch("infra.notifier.send_webhook")
    def test_failure_notification(self, mock_send):
        mock_send.return_value = True
        notify_webhook_task_complete(
            "https://hooks.slack.com/xxx", "MyAction", False,
            "error msg", "00:05"
        )
        args = mock_send.call_args
        call_kwargs = args[1] if len(args) > 1 and isinstance(args[1], dict) else args.kwargs
        title = call_kwargs.get("title", "")
        color = call_kwargs.get("color", "")
        assert "失敗" in title
        assert color == "#ff0000"
