# -*- coding: utf-8 -*-
"""server.py API エンドポイントのテスト"""
import json
import tempfile
from pathlib import Path

import pytest

import actions.csv_download  # noqa: F401
import actions.scraper  # noqa: F401
import actions.shell_cmd  # noqa: F401
import actions.file_ops  # noqa: F401

from core.config_manager import ConfigManager
from web.server import WebServer


@pytest.fixture
def client():
    config = ConfigManager()
    config.load()
    server = WebServer(config, port=5099)
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


class TestStatusAPI:

    def test_status(self, client):
        r = client.get("/api/status")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "groups" in data
        assert "running" in data
        assert "history" in data

    def test_stats(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "total" in data
        assert "success_rate" in data
        assert "by_action" in data

    def test_execution_history(self, client):
        r = client.get("/api/execution-history")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "history" in data


class TestConfigAPI:

    def test_action_types(self, client):
        r = client.get("/api/config/action-types")
        assert r.status_code == 200
        data = json.loads(r.data)
        types = [t["type"] for t in data["types"]]
        assert "scraper" in types
        assert "file_ops" in types
        assert "csv_download" in types
        assert "shell_cmd" in types

    def test_scraper_schema_has_mode(self, client):
        r = client.get("/api/config/action-types")
        data = json.loads(r.data)
        scraper_fields = data["schemas"]["scraper"]["fields"]
        mode_field = [f for f in scraper_fields if f["key"] == "mode"]
        assert len(mode_field) == 1
        assert mode_field[0]["type"] == "select"

    def test_scraper_schema_has_show_when(self, client):
        r = client.get("/api/config/action-types")
        data = json.loads(r.data)
        scraper_fields = data["schemas"]["scraper"]["fields"]
        sw_fields = [f for f in scraper_fields if "show_when" in f]
        assert len(sw_fields) >= 7  # table_index, selectors, output, output_sheet, cdp_url, form_fills, download_button, ...

    def test_file_ops_schema(self, client):
        r = client.get("/api/config/action-types")
        data = json.loads(r.data)
        fo_fields = [f["key"] for f in data["schemas"]["file_ops"]["fields"]]
        assert "operation" in fo_fields
        assert "source" in fo_fields
        assert "destination" in fo_fields
        assert "pattern" in fo_fields


class TestScrapePreviewAPI:

    def test_missing_url(self, client):
        r = client.post("/api/scrape/preview",
                        json={"mode": "auto_table"},
                        content_type="application/json")
        assert r.status_code == 400

    def test_unsupported_mode(self, client):
        r = client.post("/api/scrape/preview",
                        json={"mode": "browser_csv", "url": "http://x"},
                        content_type="application/json")
        assert r.status_code == 400

    def test_css_selector_missing_selectors(self, client):
        r = client.post("/api/scrape/preview",
                        json={"mode": "css_selector", "url": "http://x"},
                        content_type="application/json")
        assert r.status_code == 400


class TestTemplatesAPI:

    def test_list_templates(self, client):
        r = client.get("/api/templates")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "templates" in data
        names = [t["name"] for t in data["templates"]]
        assert "日付入力 → CSVダウンロード" in names
        assert "URLアクセスでCSVダウンロード" in names

    def test_get_template(self, client):
        r = client.get("/api/templates/browser_csv_date_only")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["type"] == "scraper"
        assert "params" in data

    def test_get_nonexistent_template(self, client):
        r = client.get("/api/templates/nonexistent_xxx")
        assert r.status_code == 404

    def test_save_and_delete_template(self, client):
        # Save
        r = client.post("/api/templates",
                        json={
                            "name": "test_tmpl",
                            "description": "test",
                            "type": "shell_cmd",
                            "params": {"command": "echo hi"},
                        },
                        content_type="application/json")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "ok"
        tmpl_id = data["id"]

        # Verify
        r = client.get(f"/api/templates/{tmpl_id}")
        assert r.status_code == 200

        # Delete
        r = client.delete(f"/api/templates/{tmpl_id}")
        assert r.status_code == 200

        # Verify deleted
        r = client.get(f"/api/templates/{tmpl_id}")
        assert r.status_code == 404

    def test_save_template_without_name(self, client):
        r = client.post("/api/templates",
                        json={"type": "scraper", "params": {}},
                        content_type="application/json")
        assert r.status_code == 400


class TestDryrunAPI:

    def test_dryrun_nonexistent_action(self, client):
        r = client.post("/api/dryrun/action/nonexistent_xxx",
                        json={},
                        content_type="application/json")
        assert r.status_code == 404

    def test_dryrun_returns_resolved_params(self, client):
        """ドライラン: 設定があればresolved_paramsが返る"""
        # 最初にアクションを追加
        client.post("/api/config/actions",
                     json={
                         "id": "test_dryrun",
                         "name": "DryRunTest",
                         "type": "shell_cmd",
                         "group": "",
                         "params": {"command": "echo {today}"},
                     },
                     content_type="application/json")
        r = client.post("/api/dryrun/action/test_dryrun",
                        json={"dt_from": "2026-03-05T00:00", "dt_to": "2026-03-06T00:00"},
                        content_type="application/json")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "resolved_params" in data
        assert "valid" in data
        assert data["resolved_params"]["command"] != "echo {today}"  # 変数が展開されている
        # クリーンアップ
        client.delete("/api/config/actions/test_dryrun")


class TestSSEEndpoint:

    def test_sse_endpoint_exists(self, client):
        """SSEエンドポイントが200を返す"""
        r = client.get("/api/events")
        assert r.status_code == 200
        assert "text/event-stream" in r.content_type


class TestStatsDaily:

    def test_stats_has_daily(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "daily" in data
        # 7日分のキーがある
        assert len(data["daily"]) == 7


class TestDuplicateAPI:

    def test_duplicate_action(self, client):
        """アクション複製"""
        # 元アクションを作成
        client.post("/api/config/actions",
                     json={"id": "dup_orig", "name": "Original", "type": "shell_cmd",
                           "group": "", "params": {"command": "echo test"}},
                     content_type="application/json")
        # 複製
        r = client.post("/api/config/actions/dup_orig/duplicate",
                        content_type="application/json")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert data["action"]["id"] == "dup_orig_copy"
        assert "コピー" in data["action"]["name"]
        # クリーンアップ
        client.delete("/api/config/actions/dup_orig")
        client.delete("/api/config/actions/dup_orig_copy")

    def test_duplicate_nonexistent(self, client):
        r = client.post("/api/config/actions/nonexistent_xxx/duplicate",
                        content_type="application/json")
        assert r.status_code == 404


class TestUndoAPI:

    def test_soft_delete_and_undo(self, client):
        """ソフトデリート + Undo"""
        # アクションを作成
        client.post("/api/config/actions",
                     json={"id": "undo_test", "name": "UndoTest", "type": "shell_cmd",
                           "group": "", "params": {"command": "echo hi"}},
                     content_type="application/json")
        # ソフトデリート
        r = client.delete("/api/config/actions/undo_test/soft-delete")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["undo_available"] is True

        # 削除確認
        r = client.get("/api/config/actions")
        actions = json.loads(r.data)["actions"]
        assert all(a["id"] != "undo_test" for a in actions)

        # Undo
        r = client.post("/api/config/undo", content_type="application/json")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert data["restored"]["id"] == "undo_test"

        # 復元確認
        r = client.get("/api/config/actions")
        actions = json.loads(r.data)["actions"]
        assert any(a["id"] == "undo_test" for a in actions)

        # クリーンアップ
        client.delete("/api/config/actions/undo_test")

    def test_undo_without_buffer(self, client):
        r = client.post("/api/config/undo", content_type="application/json")
        assert r.status_code == 404


class TestExportImportAPI:

    def test_export(self, client):
        r = client.get("/api/config/export")
        assert r.status_code == 200
        assert "application/x-yaml" in r.content_type
        assert b"actions" in r.data

    def test_import(self, client):
        yaml_content = """
groups:
  - name: ImportTestGroup
    display_order: 99
    color: "#FF0000"
    icon: "T"
actions:
  - id: import_test_action
    name: ImportTest
    type: shell_cmd
    params:
      command: echo imported
"""
        r = client.post("/api/config/import",
                        json={"yaml": yaml_content},
                        content_type="application/json")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["imported"]["actions"] >= 1

        # クリーンアップ
        client.delete("/api/config/actions/import_test_action")
        client.delete("/api/config/groups/ImportTestGroup")

    def test_import_invalid_yaml(self, client):
        r = client.post("/api/config/import",
                        json={"yaml": ":::invalid"},
                        content_type="application/json")
        assert r.status_code == 400

    def test_import_empty(self, client):
        r = client.post("/api/config/import",
                        json={},
                        content_type="application/json")
        assert r.status_code == 400


class TestSearchAPI:

    def test_search_empty(self, client):
        r = client.get("/api/config/search?q=")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["actions"] == []
        assert data["groups"] == []

    def test_search_actions(self, client):
        # テスト用アクションを作成
        client.post("/api/config/actions",
                     json={"id": "search_test", "name": "SearchableAction", "type": "shell_cmd",
                           "group": "", "params": {}},
                     content_type="application/json")
        r = client.get("/api/config/search?q=searchable")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert any(a["id"] == "search_test" for a in data["actions"])
        # クリーンアップ
        client.delete("/api/config/actions/search_test")


class TestHealthAPI:

    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "actions" in data
        assert "groups" in data


class TestLogsAPI:

    def test_logs(self, client):
        r = client.get("/api/logs")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "lines" in data
        assert "available_dates" in data

    def test_logs_with_filter(self, client):
        r = client.get("/api/logs?level=ERROR&lines=10")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "lines" in data


class TestExecutionHistoryExport:

    def test_csv_export(self, client):
        r = client.get("/api/execution-history/export")
        assert r.status_code == 200
        assert "text/csv" in r.content_type
        assert b"timestamp" in r.data  # CSVヘッダー


class TestHTMLPages:

    def test_index_page(self, client):
        r = client.get("/")
        assert r.status_code == 200
        html = r.data.decode()
        assert "statsGrid" in html
        assert "EventSource" in html  # SSE対応
        assert "completionCard" in html  # 完了サマリー
        assert "dryrunBtn" in html  # ドライランボタン
        assert "welcomeGuide" in html  # ウェルカムガイド

    def test_help_page(self, client):
        r = client.get("/help")
        assert r.status_code == 200
        html = r.data.decode()
        assert "テンプレート変数" in html
        assert "FAQ" in html
        assert "アクションタイプ" in html

    def test_editor_page(self, client):
        r = client.get("/editor")
        assert r.status_code == 200
        html = r.data.decode()
        assert "templateList" in html
        assert "aWebhook" in html
        assert "key_value" in html
        assert "condition.field" in html
        assert "help-icon" in html  # ツールチップアイコン
        assert "field-error" in html  # バリデーションCSS
        assert "sidebarSearch" in html  # 検索バー
        assert "duplicateAction" in html  # 複製ボタン
        assert "exportConfig" in html  # エクスポート
        assert "Ctrl" in html or "ctrl" in html.lower()  # キーボードショートカット
