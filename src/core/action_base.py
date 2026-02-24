# -*- coding: utf-8 -*-
"""
kai_system - アクション基底クラス
全てのアクションプラグインが継承する抽象基底クラス
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional


@dataclass
class ActionResult:
    """アクション実行結果"""

    success: bool
    message: str = ""
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0

    @property
    def elapsed_str(self) -> str:
        secs = self.elapsed_seconds
        minutes = int(secs // 60)
        seconds = int(secs % 60)
        return f"{minutes:02d}:{seconds:02d}"


# 進捗コールバック型: (message: str, percent: float) -> None
ProgressCallback = Callable[[str, float], None]


class ActionBase(ABC):
    """
    アクションプラグインの基底クラス

    全てのアクション（CSVダウンロード、スクレーピング、シェルコマンド等）は
    このクラスを継承して実装する。
    """

    # サブクラスでオーバーライドすべきクラス変数
    ACTION_TYPE: str = ""           # アクションタイプ名（YAMLの type フィールドと対応）
    ACTION_LABEL: str = ""          # 表示用ラベル
    ACTION_DESCRIPTION: str = ""    # アクションの説明

    def __init__(self):
        self._progress_callback: Optional[ProgressCallback] = None
        self._stop_requested: bool = False

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """進捗コールバックを設定"""
        self._progress_callback = callback

    def request_stop(self) -> None:
        """中断リクエスト"""
        self._stop_requested = True

    def reset(self) -> None:
        """状態リセット"""
        self._stop_requested = False

    def _notify_progress(self, message: str, percent: float = -1) -> None:
        """進捗を通知"""
        if self._progress_callback:
            self._progress_callback(message, percent)

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ActionResult:
        """
        アクションを実行する

        Args:
            params: YAML設定の params セクション

        Returns:
            ActionResult: 実行結果
        """
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> list:
        """
        パラメータのバリデーション

        Args:
            params: チェック対象のパラメータ

        Returns:
            問題のリスト（空なら OK）
        """
        pass

    def execute_safe(self, params: Dict[str, Any]) -> ActionResult:
        """
        安全にアクションを実行する（例外キャッチ付き）
        """
        self.reset()
        started = datetime.now()
        try:
            result = self.execute(params)
            result.started_at = started
            result.finished_at = datetime.now()
            return result
        except Exception as e:
            return ActionResult(
                success=False,
                message="実行中にエラーが発生しました",
                error=str(e),
                started_at=started,
                finished_at=datetime.now(),
            )
