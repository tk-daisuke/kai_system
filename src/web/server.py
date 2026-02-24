# -*- coding: utf-8 -*-
"""
kai_system - Flask Web UI サーバー
ブラウザベースのアクション管理画面を提供する
"""

import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template, request

from core.config_manager import ConfigManager
from core.action_manager import ActionManager, registry
from core.group_manager import GroupManager
from core.template_engine import get_template_variables, TZ_JST
from infra.logger import logger


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

        self.app = self._create_app()

    def _create_app(self) -> Flask:
        app = Flask(__name__, template_folder="templates", static_folder="static")

        @app.route("/")
        def index():
            return render_template("index.html")

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
                    else:
                        self._add_history(f"{action.name}: 失敗 - {result.error}", "error")
                except Exception as e:
                    self._add_history(f"エラー: {e}", "error")
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
