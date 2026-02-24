# -*- coding: utf-8 -*-
"""
kai_system - アクション管理モジュール
プラグインの登録・検索・実行を管理する
"""

from typing import Callable, Dict, List, Optional, Type

from core.action_base import ActionBase, ActionResult, ProgressCallback
from core.config_manager import ActionConfig, ConfigManager
from core.template_engine import expand_params
from infra.logger import logger
from infra.notifier import notify_task_complete

import time as time_module
from datetime import datetime


class ActionRegistry:
    """アクションプラグインのレジストリ"""

    def __init__(self):
        self._registry: Dict[str, Type[ActionBase]] = {}

    def register(self, action_class: Type[ActionBase]) -> None:
        """アクションクラスを登録"""
        action_type = action_class.ACTION_TYPE
        if not action_type:
            raise ValueError(f"ACTION_TYPE が設定されていません: {action_class.__name__}")
        self._registry[action_type] = action_class
        logger.info(f"アクション登録: {action_type} -> {action_class.__name__}")

    def get(self, action_type: str) -> Optional[Type[ActionBase]]:
        """タイプ名からアクションクラスを取得"""
        return self._registry.get(action_type)

    def get_all_types(self) -> List[str]:
        """登録済みの全アクションタイプ名を取得"""
        return list(self._registry.keys())


# グローバルレジストリ
registry = ActionRegistry()


def register_action(action_class: Type[ActionBase]) -> Type[ActionBase]:
    """デコレータ: アクションクラスをレジストリに登録"""
    registry.register(action_class)
    return action_class


class ActionManager:
    """アクションの実行管理"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self._progress_callback: Optional[Callable] = None
        self.stop_requested = False
        self.dt_from: Optional[datetime] = None
        self.dt_to: Optional[datetime] = None
        self.tz_mode: str = "jst"  # デフォルトTZ（アクション別に上書き）

    def set_progress_callback(self, callback: Callable) -> None:
        """GUI進捗コールバックを設定"""
        self._progress_callback = callback

    def request_stop(self) -> None:
        """中断リクエスト"""
        self.stop_requested = True

    def _notify(self, message: str, current: int = 0, total: int = 0) -> None:
        """進捗を通知"""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def run_action(self, action_config: ActionConfig) -> ActionResult:
        """
        単一アクションを実行する

        Args:
            action_config: 実行するアクションの設定

        Returns:
            ActionResult
        """
        # アクションクラスを取得
        action_class = registry.get(action_config.type)
        if action_class is None:
            msg = f"未登録のアクションタイプ: {action_config.type}"
            logger.error(msg)
            return ActionResult(success=False, message=msg, error=msg)

        # インスタンス生成
        action = action_class()

        # 進捗コールバックの橋渡し
        def on_action_progress(message: str, percent: float) -> None:
            self._notify(f"{action_config.name}: {message}")

        action.set_progress_callback(on_action_progress)

        # テンプレート変数の展開（{from}, {to}, {from_jst}, {from_utc} 等）
        # アクションの timezone 設定で汎用変数の解決先が切り替わる
        action_tz = getattr(action_config, 'timezone', self.tz_mode) or self.tz_mode
        resolved_params = expand_params(
            action_config.params,
            dt_from=self.dt_from,
            dt_to=self.dt_to,
            tz_mode=action_tz,
        )

        # バリデーション
        issues = action.validate_params(resolved_params)
        if issues:
            msg = f"パラメータエラー: {', '.join(issues)}"
            logger.error(f"[{action_config.id}] {msg}")
            return ActionResult(success=False, message=msg, error=msg)

        # 実行
        logger.info(f"アクション開始: [{action_config.id}] {action_config.name}")
        self._notify(f"実行中: {action_config.name}")

        result = action.execute_safe(resolved_params)

        if result.success:
            logger.success(
                f"アクション完了: [{action_config.id}] {action_config.name} "
                f"({result.elapsed_str})"
            )
        else:
            logger.error(
                f"アクション失敗: [{action_config.id}] {action_config.name} "
                f"- {result.error}"
            )

        return result

    def run_action_by_id(self, action_id: str) -> ActionResult:
        """IDを指定してアクションを実行"""
        action_config = self.config.get_action_by_id(action_id)
        if action_config is None:
            msg = f"アクションが見つかりません: {action_id}"
            logger.error(msg)
            return ActionResult(success=False, message=msg, error=msg)

        return self.run_action(action_config)

    def run_group(self, group_name: str) -> Dict[str, int]:
        """
        グループ内の全アクションを順次実行

        Args:
            group_name: グループ名

        Returns:
            実行結果の辞書 {"success": int, "failed": int, "skipped": int}
        """
        actions = self.config.get_actions_by_group(group_name)
        self.stop_requested = False

        results = {"success": 0, "failed": 0, "skipped": 0}
        total = len(actions)

        if total == 0:
            logger.warning(f"グループ '{group_name}' にアクションがありません")
            return results

        logger.info(f"グループ実行開始: {group_name} ({total} 件)")
        self._notify(f"グループ実行: {group_name}", 0, total)

        start_time = datetime.now()

        for i, action_config in enumerate(actions, 1):
            if self.stop_requested:
                logger.warning("ユーザーにより中断されました")
                self._notify("中断されました", i - 1, total)
                break

            if not action_config.enabled:
                results["skipped"] += 1
                self._notify(f"スキップ: {action_config.name}", i, total)
                continue

            self._notify(f"実行中 ({i}/{total}): {action_config.name}", i, total)

            result = self.run_action(action_config)

            if result.success:
                results["success"] += 1
            else:
                results["failed"] += 1

        elapsed = datetime.now() - start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        elapsed_str = f"{minutes}分{seconds}秒"

        logger.info(
            f"グループ実行完了: {group_name} - "
            f"成功={results['success']}, 失敗={results['failed']}, "
            f"スキップ={results['skipped']} ({elapsed_str})"
        )
        self._notify(f"完了: {group_name}", total, total)

        # 通知
        notify_task_complete(
            results["success"], results["failed"], results["skipped"], elapsed_str
        )

        return results
