# -*- coding: utf-8 -*-
"""
kai_system - グループ管理モジュール
グループの取得・操作を管理する
"""

from typing import Dict, List, Optional

from core.config_manager import ActionConfig, ConfigManager, GroupConfig
from infra.logger import logger


class GroupManager:
    """グループ管理クラス"""

    def __init__(self, config: ConfigManager):
        self.config = config

    def get_groups(self) -> List[GroupConfig]:
        """全グループ設定を取得（表示順）"""
        return self.config.get_groups()

    def get_group_names(self) -> List[str]:
        """グループ名のリストを取得"""
        return self.config.get_group_names()

    def get_group_actions(self, group_name: str) -> List[ActionConfig]:
        """指定グループのアクション一覧を取得"""
        return self.config.get_actions_by_group(group_name)

    def get_grouped_actions(self) -> Dict[str, List[ActionConfig]]:
        """全グループのアクションをグループ名でマッピング"""
        result: Dict[str, List[ActionConfig]] = {}
        for group in self.get_groups():
            actions = self.get_group_actions(group.name)
            if actions:
                result[group.name] = actions
        return result

    def get_group_config(self, group_name: str) -> Optional[GroupConfig]:
        """グループ設定を名前で取得"""
        for group in self.get_groups():
            if group.name == group_name:
                return group
        return None

    def get_action_count(self, group_name: str) -> int:
        """グループ内のアクション数を取得"""
        return len(self.get_group_actions(group_name))
