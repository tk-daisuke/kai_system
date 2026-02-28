# -*- coding: utf-8 -*-
"""
kai_system - Flask Web UI サーバー
ブラウザベースのアクション管理画面を提供する
"""

import json
import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from flask import Flask, jsonify, render_template, request

from core.config_manager import ConfigManager
from core.action_manager import ActionManager, registry
from core.group_manager import GroupManager
from core.template_engine import get_template_variables, TZ_JST
from core.param_schema import PARAM_SCHEMAS, get_action_types, get_param_schema
from infra.logger import logger
from infra.notifier import notify_webhook_task_complete


class WebServer:
    """Flask ベースの Web UI サーバー"""

    def __init__(self, config: ConfigManager, port: int = 5000):
        self.config = config
        self.port = port

        self.action_manager = ActionManager(config)
        self.action_manager.set_progress_callback(self._on_progress)
        self.group_manager = GroupManager(config)

        self.running_task: Optional[str] = None
        self.progress_message: str = "待機中"
        self.progress_current: int = 0
        self.progress_total: int = 0
        self.history: List[Dict] = []

        # テンプレートディレクトリ
        self.templates_dir = Path(config.config_dir) / "templates"
        self.templates_dir.mkdir(exist_ok=True)

        # 実行履歴の永続化
        self.history_file = Path(config.config_dir) / "execution_history.json"
        self.execution_history: List[Dict] = self._load_execution_history()

        self.app = self._create_app()

    def _create_app(self) -> Flask:
        app = Flask(__name__, template_folder="templates", static_folder="static")

        @app.route("/")
        def index():
            return render_template("index.html")

        @app.route("/editor")
        def editor():
            return render_template("editor.html")

        @app.route("/api/status")
        def api_status():
            groups = []
            for g in self.group_manager.get_groups():
                actions = []
                for a in self.group_manager.get_group_actions(g.name):
                    actions.append({
                        "id": a.id, "name": a.name, "type": a.type,
                        "icon": a.icon, "enabled": a.enabled,
                        "timezone": a.timezone,
                    })
                groups.append({
                    "name": g.name, "icon": g.icon,
                    "color": g.color, "actions": actions,
                })

            return jsonify({
                "groups": groups,
                "running": self.running_task,
                "progress": {
                    "message": self.progress_message,
                    "current": self.progress_current,
                    "total": self.progress_total,
                },
                "history": self.history[-50:],
                "template_vars": get_template_variables(),
            })

        @app.route("/api/run/action/<action_id>", methods=["POST"])
        def api_run_action(action_id):
            if self.running_task:
                return jsonify({"error": "別のタスクが実行中です"}), 409
            action = self.config.get_action_by_id(action_id)
            if not action:
                return jsonify({"error": f"アクションが見つかりません: {action_id}"}), 404

            dt_from, dt_to = self._parse_datetime_range(request.get_json(silent=True))
            self.running_task = action.name
            tz_label = action.timezone.upper()
            period = self._format_period(dt_from, dt_to)
            self._add_history(f"=== {action.name} [{tz_label}] 開始 {period} ===", "info")

            def run():
                try:
                    self.action_manager.dt_from = dt_from
                    self.action_manager.dt_to = dt_to
                    result = self.action_manager.run_action(action)
                    if result.success:
                        self._add_history(f"{action.name}: 完了 ({result.elapsed_str})", "success")
                        self._record_execution(action.name, action.type, True, result.elapsed_str)
                    else:
                        self._add_history(f"{action.name}: 失敗 - {result.error}", "error")
                        self._record_execution(action.name, action.type, False, result.elapsed_str, result.error or "")
                    if action.webhook_url:
                        notify_webhook_task_complete(
                            action.webhook_url, action.name,
                            result.success, result.message, result.elapsed_str
                        )
                except Exception as e:
                    self._add_history(f"エラー: {e}", "error")
                    self._record_execution(action.name, action.type, False, "", str(e))
                finally:
                    self.running_task = None
                    self.progress_message = "待機中"
                    self.action_manager.dt_from = None
                    self.action_manager.dt_to = None

            threading.Thread(target=run, daemon=True).start()
            return jsonify({"status": "started", "action": action.name})

        @app.route("/api/run/group/<group_name>", methods=["POST"])
        def api_run_group(group_name):
            if self.running_task:
                return jsonify({"error": "別のタスクが実行中です"}), 409
            actions = self.config.get_actions_by_group(group_name)
            if not actions:
                return jsonify({"error": f"グループにアクションがありません: {group_name}"}), 404

            dt_from, dt_to = self._parse_datetime_range(request.get_json(silent=True))
            self.running_task = f"グループ: {group_name}"
            period = self._format_period(dt_from, dt_to)
            self._add_history(f"=== {group_name} グループ実行開始 {period} ===", "info")

            def run():
                try:
                    self.action_manager.dt_from = dt_from
                    self.action_manager.dt_to = dt_to
                    results = self.action_manager.run_group(group_name)
                    self._add_history(
                        f"=== {group_name} 完了: 成功={results['success']}, "
                        f"失敗={results['failed']}, スキップ={results['skipped']} ===",
                        "success" if results["failed"] == 0 else "error",
                    )
                except Exception as e:
                    self._add_history(f"グループ実行エラー: {e}", "error")
                finally:
                    self.running_task = None
                    self.progress_message = "待機中"
                    self.action_manager.dt_from = None
                    self.action_manager.dt_to = None

            threading.Thread(target=run, daemon=True).start()
            return jsonify({"status": "started", "group": group_name})

        @app.route("/api/stop", methods=["POST"])
        def api_stop():
            self.action_manager.request_stop()
            self._add_history("中断をリクエストしました", "warning")
            return jsonify({"status": "stop_requested"})

        @app.route("/api/reload", methods=["POST"])
        def api_reload():
            self.config.reload()
            self._add_history("設定を再読み込みしました", "info")
            return jsonify({"status": "reloaded"})

        @app.route("/api/preview_vars", methods=["POST"])
        def api_preview_vars():
            data = request.get_json(silent=True) or {}
            dt_from, dt_to = self._parse_datetime_range(data)
            tz = data.get("tz_mode", "jst")
            vars = get_template_variables(dt_from=dt_from, dt_to=dt_to, tz_mode=tz)
            return jsonify({"vars": vars})

        # ──────── 設定エディタAPI ────────

        @app.route("/api/config/actions", methods=["GET"])
        def api_config_get_actions():
            actions = [a.to_dict() for a in self.config._actions]
            return jsonify({"actions": actions})

        @app.route("/api/config/actions", methods=["POST"])
        def api_config_add_action():
            data = request.get_json(silent=True) or {}
            try:
                self.config.backup_config()
                action = self.config.add_action(data)
                self.config.save_actions()
                return jsonify({"status": "ok", "action": action.to_dict()})
            except (ValueError, KeyError) as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @app.route("/api/config/actions/<action_id>", methods=["PUT"])
        def api_config_update_action(action_id):
            data = request.get_json(silent=True) or {}
            try:
                self.config.backup_config()
                action = self.config.update_action(action_id, data)
                self.config.save_actions()
                return jsonify({"status": "ok", "action": action.to_dict()})
            except (ValueError, KeyError) as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @app.route("/api/config/actions/<action_id>", methods=["DELETE"])
        def api_config_delete_action(action_id):
            try:
                self.config.backup_config()
                self.config.delete_action(action_id)
                self.config.save_actions()
                return jsonify({"status": "ok"})
            except KeyError as e:
                return jsonify({"status": "error", "message": str(e)}), 404

        @app.route("/api/config/actions/reorder", methods=["POST"])
        def api_config_reorder_actions():
            data = request.get_json(silent=True) or {}
            id_list = data.get("ids", [])
            self.config.backup_config()
            self.config.reorder_actions(id_list)
            self.config.save_actions()
            return jsonify({"status": "ok"})

        @app.route("/api/config/groups", methods=["GET"])
        def api_config_get_groups():
            groups = [g.to_dict() for g in self.config._groups]
            return jsonify({"groups": groups})

        @app.route("/api/config/groups", methods=["POST"])
        def api_config_add_group():
            data = request.get_json(silent=True) or {}
            try:
                self.config.backup_config()
                group = self.config.add_group(data)
                self.config.save_groups()
                return jsonify({"status": "ok", "group": group.to_dict()})
            except (ValueError, KeyError) as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @app.route("/api/config/groups/<group_name>", methods=["PUT"])
        def api_config_update_group(group_name):
            data = request.get_json(silent=True) or {}
            try:
                self.config.backup_config()
                group = self.config.update_group(group_name, data)
                self.config.save_groups()
                self.config.save_actions()  # グループ名変更時にアクションも更新
                return jsonify({"status": "ok", "group": group.to_dict()})
            except (ValueError, KeyError) as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @app.route("/api/config/groups/<group_name>", methods=["DELETE"])
        def api_config_delete_group(group_name):
            try:
                self.config.backup_config()
                self.config.delete_group(group_name)
                self.config.save_groups()
                self.config.save_actions()  # 所属アクションのgroupフィールド更新
                return jsonify({"status": "ok"})
            except KeyError as e:
                return jsonify({"status": "error", "message": str(e)}), 404

        @app.route("/api/config/action-types", methods=["GET"])
        def api_config_action_types():
            return jsonify({
                "types": get_action_types(),
                "schemas": PARAM_SCHEMAS,
            })

        # ──────── テンプレート管理API ────────

        @app.route("/api/templates", methods=["GET"])
        def api_templates_list():
            templates = []
            for f in sorted(self.templates_dir.glob("*.yaml")):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                    templates.append({
                        "id": f.stem,
                        "name": data.get("name", f.stem),
                        "description": data.get("description", ""),
                        "type": data.get("type", ""),
                        "params": data.get("params", {}),
                    })
                except Exception as e:
                    logger.warning(f"テンプレート読み込みエラー: {f}: {e}")
            return jsonify({"templates": templates})

        @app.route("/api/templates/<template_id>", methods=["GET"])
        def api_template_get(template_id):
            filepath = self.templates_dir / f"{template_id}.yaml"
            if not filepath.exists():
                return jsonify({"error": "テンプレートが見つかりません"}), 404
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return jsonify({
                    "id": template_id,
                    "name": data.get("name", template_id),
                    "description": data.get("description", ""),
                    "type": data.get("type", ""),
                    "params": data.get("params", {}),
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/templates", methods=["POST"])
        def api_template_save():
            data = request.get_json(silent=True) or {}
            name = data.get("name", "").strip()
            if not name:
                return jsonify({"error": "テンプレート名が指定されていません"}), 400

            # ファイル名安全化
            safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            filepath = self.templates_dir / f"{safe_id}.yaml"

            template_data = {
                "name": name,
                "description": data.get("description", ""),
                "type": data.get("type", ""),
                "params": data.get("params", {}),
            }
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(template_data, f, allow_unicode=True, default_flow_style=False)
                return jsonify({"status": "ok", "id": safe_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/templates/<template_id>", methods=["DELETE"])
        def api_template_delete(template_id):
            filepath = self.templates_dir / f"{template_id}.yaml"
            if not filepath.exists():
                return jsonify({"error": "テンプレートが見つかりません"}), 404
            try:
                filepath.unlink()
                return jsonify({"status": "ok"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ──────── 実行履歴・統計API ────────

        @app.route("/api/stats")
        def api_stats():
            return jsonify(self._get_stats())

        @app.route("/api/execution-history")
        def api_execution_history():
            limit = request.args.get("limit", 50, type=int)
            return jsonify({"history": self.execution_history[-limit:]})

        # ──────── スクレーピングプレビューAPI ────────

        @app.route("/api/scrape/preview", methods=["POST"])
        def api_scrape_preview():
            """auto_table / css_selector モードの取得結果を先頭10行プレビュー"""
            data = request.get_json(silent=True) or {}
            mode = data.get("mode", "")
            url = data.get("url", "")

            if not url:
                return jsonify({"error": "URL が指定されていません"}), 400
            if mode not in ("auto_table", "css_selector"):
                return jsonify({"error": "プレビューは auto_table / css_selector モードのみ対応です"}), 400

            try:
                import pandas as pd
                import requests as http_requests

                resp = http_requests.get(url, timeout=30)
                resp.raise_for_status()

                if mode == "auto_table":
                    table_index = data.get("table_index", 0)
                    tables = pd.read_html(resp.text)
                    if not tables:
                        return jsonify({"error": "テーブルが見つかりませんでした"}), 404
                    if table_index >= len(tables):
                        return jsonify({
                            "error": f"テーブルインデックス {table_index} が範囲外（{len(tables)}個検出）"
                        }), 400
                    df = tables[table_index].head(10)
                    return jsonify({
                        "columns": list(df.columns.astype(str)),
                        "rows": df.fillna("").astype(str).values.tolist(),
                        "total_tables": len(tables),
                    })

                else:  # css_selector
                    from bs4 import BeautifulSoup
                    selectors = data.get("selectors", {})
                    if not selectors:
                        return jsonify({"error": "selectors が指定されていません"}), 400

                    soup = BeautifulSoup(resp.text, "html.parser")
                    result = {}
                    max_len = 0
                    for col, sel in selectors.items():
                        elements = soup.select(sel)
                        texts = [el.get_text(strip=True) for el in elements]
                        result[col] = texts
                        max_len = max(max_len, len(texts))

                    if max_len == 0:
                        return jsonify({"error": "一致する要素が見つかりませんでした"}), 404

                    # 先頭10行に制限 & 長さ揃え
                    columns = list(result.keys())
                    rows = []
                    for i in range(min(max_len, 10)):
                        rows.append([result[c][i] if i < len(result[c]) else "" for c in columns])

                    return jsonify({"columns": columns, "rows": rows, "total_rows": max_len})

            except ImportError as e:
                return jsonify({"error": f"必要なライブラリがありません: {e}"}), 500
            except Exception as e:
                logger.error(f"プレビューエラー: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/config/backup", methods=["POST"])
        def api_config_backup():
            ts = self.config.backup_config()
            return jsonify({"status": "ok", "timestamp": ts})

        @app.route("/api/config/backups", methods=["GET"])
        def api_config_list_backups():
            return jsonify({"backups": self.config.list_backups()})

        @app.route("/api/config/restore", methods=["POST"])
        def api_config_restore():
            data = request.get_json(silent=True) or {}
            ts = data.get("timestamp", "")
            try:
                self.config.restore_config(ts)
                return jsonify({"status": "ok"})
            except FileNotFoundError as e:
                return jsonify({"status": "error", "message": str(e)}), 404

        return app

    def _parse_datetime_range(self, data) -> tuple:
        if not data:
            return None, None
        dt_from = dt_to = None
        for key, target in [("dt_from", "from"), ("dt_to", "to")]:
            val = data.get(key)
            if val:
                try:
                    dt = datetime.strptime(val, "%Y-%m-%dT%H:%M")
                    dt = dt.replace(tzinfo=TZ_JST)
                    if target == "from":
                        dt_from = dt
                    else:
                        dt_to = dt
                except (ValueError, TypeError):
                    pass
        return dt_from, dt_to

    def _format_period(self, dt_from, dt_to) -> str:
        if dt_from and dt_to:
            f = dt_from.strftime("%m/%d %H:%M")
            t = dt_to.strftime("%m/%d %H:%M")
            return f"({f} → {t})"
        return ""

    def _load_execution_history(self) -> List[Dict]:
        """永続化された実行履歴を読み込む"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("実行履歴ファイルの読み込みに失敗しました")
        return []

    def _save_execution_history(self) -> None:
        """実行履歴を永続化する"""
        try:
            # 最新500件に制限
            data = self.execution_history[-500:]
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.warning(f"実行履歴の保存に失敗: {e}")

    def _record_execution(self, action_name: str, action_type: str, success: bool, elapsed: str, error: str = "") -> None:
        """実行結果を永続化履歴に記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "action": action_name,
            "type": action_type,
            "success": success,
            "elapsed": elapsed,
            "error": error,
        }
        self.execution_history.append(record)
        self._save_execution_history()

    def _get_stats(self) -> Dict:
        """実行統計を集計する"""
        total = len(self.execution_history)
        success = sum(1 for r in self.execution_history if r.get("success"))
        failed = total - success
        rate = round(success / total * 100, 1) if total > 0 else 0

        # 直近7日間の統計
        now = datetime.now()
        week_ago = (now - timedelta(days=7)).isoformat()
        recent = [r for r in self.execution_history if r.get("timestamp", "") >= week_ago]
        recent_total = len(recent)
        recent_success = sum(1 for r in recent if r.get("success"))

        # アクション別集計
        by_action: Dict[str, Dict] = {}
        for r in self.execution_history:
            name = r.get("action", "unknown")
            if name not in by_action:
                by_action[name] = {"total": 0, "success": 0, "failed": 0}
            by_action[name]["total"] += 1
            if r.get("success"):
                by_action[name]["success"] += 1
            else:
                by_action[name]["failed"] += 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": rate,
            "recent_7d": {"total": recent_total, "success": recent_success},
            "by_action": by_action,
        }

    def _on_progress(self, current, total, message):
        self.progress_current = current
        self.progress_total = total
        self.progress_message = message

    def _add_history(self, message, level="info"):
        self.history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message, "level": level,
        })
        logger.info(f"[HISTORY] [{level}] {message}")

    def run(self, open_browser=True):
        logger.info(f"Web UI を起動します: http://localhost:{self.port}")
        self._add_history(f"kai_system 起動 (port: {self.port})", "info")
        if open_browser:
            threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{self.port}")).start()
        self.app.run(host="127.0.0.1", port=self.port, debug=False, use_reloader=False)
