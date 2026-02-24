# -*- coding: utf-8 -*-
"""
kai_system - YAML設定管理モジュール
actions.yaml / groups.yaml からタスク設定を読み込む
"""

import sys
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
        self._raw = data

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

    def __repr__(self) -> str:
        return f"GroupConfig(name={self.name!r}, order={self.display_order})"


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
        self._loaded = False

    @property
    def actions_file(self) -> Path:
        return self.config_dir / "actions.yaml"

    @property
    def groups_file(self) -> Path:
        return self.config_dir / "groups.yaml"

    def load(self) -> None:
        """設定ファイルを読み込む"""
        self._load_groups()
        self._load_actions()
        self._loaded = True
        logger.info(
            f"設定読み込み完了: {len(self._actions)} アクション, "
            f"{len(self._groups)} グループ"
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
