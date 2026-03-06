# -*- coding: utf-8 -*-
"""
kai_system - YAML設定管理モジュール
actions.yaml / groups.yaml からタスク設定を読み込む
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from infra.logger import logger


def _get_base_path() -> Path:
    """プロジェクトルートのパスを取得"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent.parent


class ActionConfig:
    """個別アクションの設定を保持するクラス"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.type: str = data.get("type", "")
        self.group: str = data.get("group", "")
        self.enabled: bool = data.get("enabled", True)
        self.timezone: str = data.get("timezone", "jst")  # "jst" or "utc"
        self.params: Dict[str, Any] = data.get("params", {})
        self.display_order: int = data.get("display_order", 999)
        self.icon: str = data.get("icon", "▶")
        self.webhook_url: str = data.get("webhook_url", "")
        self._raw = data

    def to_dict(self) -> Dict[str, Any]:
        """YAML書き出し用の辞書を返す"""
        d: Dict[str, Any] = {"id": self.id, "name": self.name, "type": self.type}
        if self.group:
            d["group"] = self.group
        if self.icon and self.icon != "▶":
            d["icon"] = self.icon
        if self.timezone != "jst":
            d["timezone"] = self.timezone
        d["display_order"] = self.display_order
        if not self.enabled:
            d["enabled"] = False
        if self.webhook_url:
            d["webhook_url"] = self.webhook_url
        if self.params:
            d["params"] = dict(self.params)
        return d

    def __repr__(self) -> str:
        return f"ActionConfig(id={self.id!r}, name={self.name!r}, type={self.type!r}, group={self.group!r})"


class GroupConfig:
    """グループの設定を保持するクラス"""

    def __init__(self, data: Dict[str, Any]):
        self.name: str = data.get("name", "")
        self.display_order: int = data.get("display_order", 999)
        self.color: str = data.get("color", "#4CAF50")
        self.icon: str = data.get("icon", "📁")
        self._raw = data

    def to_dict(self) -> Dict[str, Any]:
        """YAML書き出し用の辞書を返す"""
        return {
            "name": self.name,
            "display_order": self.display_order,
            "color": self.color,
            "icon": self.icon,
        }

    def __repr__(self) -> str:
        return f"GroupConfig(name={self.name!r}, order={self.display_order})"


class WorkflowConfig:
    """ワークフロー (アクションの順次実行定義) を保持するクラス"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.description: str = data.get("description", "")
        self.action_ids: List[str] = data.get("action_ids", [])
        self.stop_on_error: bool = data.get("stop_on_error", True)
        self.display_order: int = data.get("display_order", 999)
        self.icon: str = data.get("icon", "&#9881;")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action_ids": self.action_ids,
            "stop_on_error": self.stop_on_error,
            "display_order": self.display_order,
            "icon": self.icon,
        }


class ConfigManager:
    """YAML設定ファイルの管理クラス"""

    DEFAULT_CONFIG_DIR = "config"

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            self.config_dir = _get_base_path() / self.DEFAULT_CONFIG_DIR
        else:
            self.config_dir = Path(config_dir)

        self._actions: List[ActionConfig] = []
        self._groups: List[GroupConfig] = []
        self._workflows: List[WorkflowConfig] = []
        self._loaded = False

    @property
    def actions_file(self) -> Path:
        return self.config_dir / "actions.yaml"

    @property
    def groups_file(self) -> Path:
        return self.config_dir / "groups.yaml"

    @property
    def workflows_file(self) -> Path:
        return self.config_dir / "workflows.yaml"

    def load(self) -> None:
        """設定ファイルを読み込む"""
        self._load_groups()
        self._load_actions()
        self._load_workflows()
        self._loaded = True
        logger.info(
            f"設定読み込み完了: {len(self._actions)} アクション, "
            f"{len(self._groups)} グループ, {len(self._workflows)} ワークフロー"
        )

    def _load_actions(self) -> None:
        """actions.yaml を読み込む"""
        if not self.actions_file.exists():
            logger.warning(f"アクション設定ファイルが見つかりません: {self.actions_file}")
            self._actions = []
            return

        try:
            with open(self.actions_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "actions" in data:
                self._actions = [ActionConfig(a) for a in data["actions"]]
                # display_order でソート
                self._actions.sort(key=lambda a: a.display_order)
            else:
                self._actions = []

        except Exception as e:
            logger.error(f"アクション設定の読み込みエラー: {e}")
            self._actions = []

    def _load_groups(self) -> None:
        """groups.yaml を読み込む"""
        if not self.groups_file.exists():
            logger.warning(f"グループ設定ファイルが見つかりません: {self.groups_file}")
            self._groups = []
            return

        try:
            with open(self.groups_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data and "groups" in data:
                self._groups = [GroupConfig(g) for g in data["groups"]]
                self._groups.sort(key=lambda g: g.display_order)
            else:
                self._groups = []

        except Exception as e:
            logger.error(f"グループ設定の読み込みエラー: {e}")
            self._groups = []

    def reload(self) -> None:
        """設定ファイルを再読み込み"""
        logger.info("設定ファイルを再読み込みします")
        self.load()

    def get_all_actions(self) -> List[ActionConfig]:
        """全アクションを取得"""
        if not self._loaded:
            self.load()
        return [a for a in self._actions if a.enabled]

    def get_action_by_id(self, action_id: str) -> Optional[ActionConfig]:
        """IDでアクションを検索"""
        for action in self.get_all_actions():
            if action.id == action_id:
                return action
        return None

    def get_actions_by_group(self, group_name: str) -> List[ActionConfig]:
        """指定グループのアクション一覧を取得"""
        return [a for a in self.get_all_actions() if a.group == group_name]

    def get_groups(self) -> List[GroupConfig]:
        """グループ一覧を取得"""
        if not self._loaded:
            self.load()
        return self._groups

    def get_group_names(self) -> List[str]:
        """グループ名の一覧を取得（表示順）"""
        return [g.name for g in self.get_groups()]

    def get_ungrouped_actions(self) -> List[ActionConfig]:
        """グループに属さないアクションを取得"""
        group_names = set(self.get_group_names())
        return [
            a for a in self.get_all_actions()
            if a.group not in group_names or a.group == ""
        ]

    def _load_workflows(self) -> None:
        """workflows.yaml を読み込む"""
        if not self.workflows_file.exists():
            self._workflows = []
            return
        try:
            with open(self.workflows_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "workflows" in data:
                self._workflows = [WorkflowConfig(w) for w in data["workflows"]]
                self._workflows.sort(key=lambda w: w.display_order)
            else:
                self._workflows = []
        except Exception as e:
            logger.error(f"ワークフロー設定の読み込みエラー: {e}")
            self._workflows = []

    def get_workflows(self) -> List[WorkflowConfig]:
        if not self._loaded:
            self.load()
        return self._workflows

    def get_workflow_by_id(self, workflow_id: str) -> Optional[WorkflowConfig]:
        for w in self.get_workflows():
            if w.id == workflow_id:
                return w
        return None

    def save_workflows(self) -> None:
        data = {"workflows": [w.to_dict() for w in self._workflows]}
        self._write_yaml(self.workflows_file, data)
        logger.info(f"ワークフロー設定を保存しました ({len(self._workflows)} 件)")

    def add_workflow(self, data: Dict[str, Any]) -> WorkflowConfig:
        if not self._loaded:
            self.load()
        new_id = data.get("id", "")
        if any(w.id == new_id for w in self._workflows):
            raise ValueError(f"ワークフローIDが重複しています: {new_id}")
        wf = WorkflowConfig(data)
        self._workflows.append(wf)
        self._workflows.sort(key=lambda w: w.display_order)
        return wf

    def update_workflow(self, workflow_id: str, data: Dict[str, Any]) -> WorkflowConfig:
        if not self._loaded:
            self.load()
        for i, w in enumerate(self._workflows):
            if w.id == workflow_id:
                new_id = data.get("id", workflow_id)
                if new_id != workflow_id and any(x.id == new_id for x in self._workflows):
                    raise ValueError(f"ワークフローIDが重複しています: {new_id}")
                data.setdefault("id", workflow_id)
                self._workflows[i] = WorkflowConfig(data)
                self._workflows.sort(key=lambda w: w.display_order)
                return self._workflows[i]
        raise KeyError(f"ワークフローが見つかりません: {workflow_id}")

    def delete_workflow(self, workflow_id: str) -> None:
        if not self._loaded:
            self.load()
        before = len(self._workflows)
        self._workflows = [w for w in self._workflows if w.id != workflow_id]
        if len(self._workflows) == before:
            raise KeyError(f"ワークフローが見つかりません: {workflow_id}")

    def validate(self) -> List[Dict[str, Any]]:
        """設定のバリデーションを行う"""
        issues = []
        action_ids = set()

        for action in self._actions:
            action_issues = []

            # ID重複チェック
            if action.id in action_ids:
                action_issues.append(f"IDが重複しています: {action.id}")
            action_ids.add(action.id)

            # 必須フィールドチェック
            if not action.id:
                action_issues.append("IDが空です")
            if not action.name:
                action_issues.append("名前が空です")
            if not action.type:
                action_issues.append("タイプが空です")

            if action_issues:
                issues.append({"action": action, "issues": action_issues})

        if issues:
            logger.warning(f"設定にエラーのあるアクション: {len(issues)} 件")
        else:
            logger.info("全アクションの設定チェック: OK")

        return issues

    # ──────── 保存系メソッド ────────

    def save_actions(self) -> None:
        """現在のアクション一覧を actions.yaml に書き出す"""
        data = {"actions": [a.to_dict() for a in self._actions]}
        self._write_yaml(self.actions_file, data)
        logger.info(f"アクション設定を保存しました ({len(self._actions)} 件)")

    def save_groups(self) -> None:
        """現在のグループ一覧を groups.yaml に書き出す"""
        data = {"groups": [g.to_dict() for g in self._groups]}
        self._write_yaml(self.groups_file, data)
        logger.info(f"グループ設定を保存しました ({len(self._groups)} 件)")

    def _write_yaml(self, path: Path, data: dict) -> None:
        """YAML を書き出す (UTF-8, 可読フォーマット)"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data, f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    # ──────── アクション CRUD ────────

    def add_action(self, data: Dict[str, Any]) -> ActionConfig:
        """アクションを追加"""
        if not self._loaded:
            self.load()
        # ID 重複チェック
        new_id = data.get("id", "")
        if any(a.id == new_id for a in self._actions):
            raise ValueError(f"ID が重複しています: {new_id}")
        action = ActionConfig(data)
        self._actions.append(action)
        self._actions.sort(key=lambda a: a.display_order)
        return action

    def update_action(self, action_id: str, data: Dict[str, Any]) -> ActionConfig:
        """既存アクションを更新"""
        if not self._loaded:
            self.load()
        for i, a in enumerate(self._actions):
            if a.id == action_id:
                # ID 変更時の重複チェック
                new_id = data.get("id", action_id)
                if new_id != action_id and any(x.id == new_id for x in self._actions):
                    raise ValueError(f"ID が重複しています: {new_id}")
                new_action = ActionConfig(data)
                self._actions[i] = new_action
                self._actions.sort(key=lambda a: a.display_order)
                return new_action
        raise KeyError(f"アクションが見つかりません: {action_id}")

    def delete_action(self, action_id: str) -> None:
        """アクションを削除"""
        if not self._loaded:
            self.load()
        before = len(self._actions)
        self._actions = [a for a in self._actions if a.id != action_id]
        if len(self._actions) == before:
            raise KeyError(f"アクションが見つかりません: {action_id}")

    def reorder_actions(self, id_list: List[str]) -> None:
        """IDリスト順に display_order を振り直す"""
        if not self._loaded:
            self.load()
        order_map = {aid: idx + 1 for idx, aid in enumerate(id_list)}
        for a in self._actions:
            if a.id in order_map:
                a.display_order = order_map[a.id]
        self._actions.sort(key=lambda a: a.display_order)

    def duplicate_action(self, action_id: str) -> ActionConfig:
        """アクションを複製する"""
        if not self._loaded:
            self.load()
        original = None
        for a in self._actions:
            if a.id == action_id:
                original = a
                break
        if not original:
            raise KeyError(f"アクションが見つかりません: {action_id}")
        data = original.to_dict()
        # 新しいIDと名前を生成
        base_id = action_id + "_copy"
        new_id = base_id
        counter = 1
        while any(a.id == new_id for a in self._actions):
            counter += 1
            new_id = f"{base_id}{counter}"
        data["id"] = new_id
        data["name"] = data.get("name", "") + " (コピー)"
        action = ActionConfig(data)
        self._actions.append(action)
        self._actions.sort(key=lambda a: a.display_order)
        return action

    # ──────── グループ CRUD ────────

    def add_group(self, data: Dict[str, Any]) -> GroupConfig:
        """グループを追加"""
        if not self._loaded:
            self.load()
        new_name = data.get("name", "")
        if any(g.name == new_name for g in self._groups):
            raise ValueError(f"グループ名が重複しています: {new_name}")
        group = GroupConfig(data)
        self._groups.append(group)
        self._groups.sort(key=lambda g: g.display_order)
        return group

    def update_group(self, group_name: str, data: Dict[str, Any]) -> GroupConfig:
        """既存グループを更新"""
        if not self._loaded:
            self.load()
        for i, g in enumerate(self._groups):
            if g.name == group_name:
                new_name = data.get("name", group_name)
                if new_name != group_name and any(x.name == new_name for x in self._groups):
                    raise ValueError(f"グループ名が重複しています: {new_name}")
                # グループ名変更時、所属アクションも更新
                if new_name != group_name:
                    for a in self._actions:
                        if a.group == group_name:
                            a.group = new_name
                self._groups[i] = GroupConfig(data)
                self._groups.sort(key=lambda g: g.display_order)
                return self._groups[i]
        raise KeyError(f"グループが見つかりません: {group_name}")

    def delete_group(self, group_name: str) -> None:
        """グループを削除（所属アクションは未分類になる）"""
        if not self._loaded:
            self.load()
        before = len(self._groups)
        self._groups = [g for g in self._groups if g.name != group_name]
        if len(self._groups) == before:
            raise KeyError(f"グループが見つかりません: {group_name}")
        # 所属アクションのグループを空にする
        for a in self._actions:
            if a.group == group_name:
                a.group = ""

    # ──────── バックアップ / 復元 ────────

    def backup_config(self) -> str:
        """設定ファイルのバックアップを作成。ファイル名を返す"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        for src in [self.actions_file, self.groups_file, self.workflows_file]:
            if src.exists():
                dst = backup_dir / f"{src.stem}_{ts}{src.suffix}"
                shutil.copy2(src, dst)

        logger.info(f"バックアップ作成: {ts}")
        return ts

    def list_backups(self) -> List[Dict[str, str]]:
        """利用可能なバックアップ一覧を返す"""
        backup_dir = self.config_dir / "backups"
        if not backup_dir.exists():
            return []
        # タイムスタンプを抽出してグループ化
        timestamps = set()
        for f in backup_dir.glob("*.yaml"):
            parts = f.stem.rsplit("_", 2)
            if len(parts) >= 3:
                ts = f"{parts[-2]}_{parts[-1]}"
                timestamps.add(ts)
        result = []
        for ts in sorted(timestamps, reverse=True):
            result.append({"timestamp": ts, "label": ts.replace("_", " ")})
        return result

    def restore_config(self, timestamp: str) -> None:
        """バックアップから復元"""
        import re as _re
        if not _re.match(r'^\d{8}_\d{6}$', timestamp):
            raise ValueError(f"無効なタイムスタンプ形式です: {timestamp}")
        backup_dir = self.config_dir / "backups"
        restored = False
        for src_name in ["actions", "groups"]:
            bak = backup_dir / f"{src_name}_{timestamp}.yaml"
            if bak.exists():
                dst = self.config_dir / f"{src_name}.yaml"
                shutil.copy2(bak, dst)
                restored = True
        if not restored:
            raise FileNotFoundError(f"バックアップが見つかりません: {timestamp}")
        self.reload()
        logger.info(f"バックアップから復元しました: {timestamp}")
